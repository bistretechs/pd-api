# ============================================================================
# VENDOR PORTAL VIEWSETS
# ============================================================================

from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import timedelta
from decimal import Decimal

from .models import (
    PurchaseOrder,
    VendorInvoice,
    PurchaseOrderProof,
    PurchaseOrderIssue,
    PurchaseOrderNote,
    MaterialSubstitutionRequest,
    Vendor,
    QCInspection,
    JobVendorStage,
)
from .vendor_portal_serializers import (
    PurchaseOrderSerializer,
    VendorInvoiceSerializer,
    PurchaseOrderProofSerializer,
    PurchaseOrderIssueSerializer,
    PurchaseOrderNoteSerializer,
    MaterialSubstitutionRequestSerializer,
    VendorPerformanceSerializer,
)
from .api_serializers import VendorSerializer
from .permissions import IsVendor


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Purchase Orders - Vendor Portal.
    Vendors can view their assigned POs and update status/milestones.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['status', 'milestone', 'job']
    search_fields = ['po_number', 'product_type', 'job__job_number']
    ordering_fields = ['created_at', 'required_by', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter POs by authenticated vendor only"""
        if not self.request.user.is_authenticated:
            return PurchaseOrder.objects.none()
        
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return PurchaseOrder.objects.filter(vendor=vendor).select_related(
                'job', 'vendor', 'job__client'
            )
        except Vendor.DoesNotExist:
            return PurchaseOrder.objects.none()
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Vendor accepts the purchase order"""
        po = self.get_object()
        po.vendor_accepted = True
        po.vendor_accepted_at = timezone.now()
        po.status = 'in_production'
        po.milestone = 'in_production'
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Purchase order accepted',
            'po_number': po.po_number
        })
    
    @action(detail=True, methods=['post'])
    def update_milestone(self, request, pk=None):
        """Update PO milestone"""
        po = self.get_object()
        milestone = request.data.get('milestone')
        notes = request.data.get('notes', '')
        
        if milestone not in dict(PurchaseOrder.MILESTONE_CHOICES):
            return Response(
                {'error': 'Invalid milestone'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        po.milestone = milestone
        if notes:
            po.vendor_notes = notes
        
        # Auto-update status based on milestone
        milestone_status_map = {
            'awaiting_acceptance': 'new',
            'in_production': 'in_production',
            'quality_check': 'quality_check',
            'completed': 'completed',
        }
        po.status = milestone_status_map.get(milestone, po.status)
        
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Milestone updated',
            'milestone': po.milestone,
            'po_status': po.status
        })
    
    @action(detail=True, methods=['post'])
    def acknowledge_assets(self, request, pk=None):
        """Mark assets as acknowledged"""
        po = self.get_object()
        po.assets_acknowledged = True
        po.assets_acknowledged_at = timezone.now()
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Assets acknowledged'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get vendor PO statistics"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Vendor profile not found'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pos = PurchaseOrder.objects.filter(vendor=vendor)
        
        stats = {
            'total_pos': pos.count(),
            'active_pos': pos.exclude(status__in=['COMPLETED', 'CANCELLED']).count(),
            'completed_pos': pos.filter(status='COMPLETED').count(),
            'at_risk_pos': pos.filter(
                status__in=['IN_PRODUCTION', 'AWAITING_APPROVAL'],
                required_by__lt=timezone.now().date()
            ).count(),
            'total_value': float(pos.aggregate(Sum('total_cost'))['total_cost__sum'] or 0),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def coordination_jobs(self, request, pk=None):
        """Get related POs in the same coordination group"""
        po = self.get_object()
        if po.coordination_group:
            related_pos = PurchaseOrder.objects.filter(
                coordination_group=po.coordination_group
            ).exclude(id=po.id)
            serializer = self.get_serializer(related_pos, many=True)
            return Response(serializer.data)
        return Response([])


class VendorInvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Invoices.
    Vendors can create and submit invoices for completed work.
    """
    queryset = VendorInvoice.objects.all()
    serializer_class = VendorInvoiceSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['vendor', 'status', 'purchase_order', 'job']
    search_fields = ['invoice_number', 'vendor_invoice_ref']
    ordering_fields = ['created_at', 'invoice_date', 'due_date', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter invoices by vendor"""
        if not self.request.user.is_authenticated:
            return VendorInvoice.objects.none()
        
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return VendorInvoice.objects.filter(vendor=vendor).select_related(
                'vendor', 'purchase_order', 'job'
            )
        except Vendor.DoesNotExist:
            return VendorInvoice.objects.none()
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        purchase_order_id = request.data.get('purchase_order_id')
        
        try:
            purchase_order = PurchaseOrder.objects.get(
                id=purchase_order_id,
                vendor=vendor
            )
        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate totals
        line_items = request.data.get('line_items', [])
        subtotal = request.data.get('subtotal', 0)
        tax_rate = request.data.get('tax_rate', 16)
        
        invoice = VendorInvoice.objects.create(
            vendor=vendor,
            purchase_order=purchase_order,
            job=purchase_order.job,
            vendor_invoice_ref=request.data.get('vendor_invoice_ref', ''),
            invoice_date=request.data.get('invoice_date'),
            due_date=request.data.get('due_date'),
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=tax_rate,
            status='draft'
        )
        
        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get invoice statistics for vendor"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response({
                'draft_count': 0,
                'submitted_count': 0,
                'approved_count': 0,
                'paid_count': 0,
                'rejected_count': 0,
                'total_pending_amount': 0,
                'total_paid_amount': 0,
                'current_month_amount': 0,
            })
        
        invoices = VendorInvoice.objects.filter(vendor=vendor)
        
        from django.db.models import Sum
        from datetime import datetime
        
        stats = {
            'draft_count': invoices.filter(status='draft').count(),
            'submitted_count': invoices.filter(status='submitted').count(),
            'approved_count': invoices.filter(status='approved').count(),
            'paid_count': invoices.filter(status='paid').count(),
            'rejected_count': invoices.filter(status='rejected').count(),
            'total_pending_amount': float(
                invoices.filter(status__in=['submitted', 'approved']).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            ),
            'total_paid_amount': float(
                invoices.filter(status='paid').aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            ),
            'current_month_amount': float(
                invoices.filter(
                    invoice_date__month=datetime.now().month,
                    invoice_date__year=datetime.now().year
                ).aggregate(total=Sum('total_amount'))['total'] or 0
            ),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit invoice for review"""
        invoice = self.get_object()
        
        if invoice.status != 'draft':
            return Response(
                {'error': 'Only draft invoices can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'submitted'
        invoice.submitted_at = timezone.now()
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve invoice (Production Team only)"""
        invoice = self.get_object()
        
        if invoice.status != 'submitted':
            return Response(
                {'error': 'Only submitted invoices can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'approved'
        invoice.approved_at = timezone.now()
        invoice.approved_by = request.user
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'Invoice approved',
            'invoice_number': invoice.invoice_number
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject invoice with reason"""
        invoice = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'rejected'
        invoice.rejection_reason = reason
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'Invoice rejected',
            'invoice_number': invoice.invoice_number
        })


class PurchaseOrderProofViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Proofs - Vendor Portal"""
    queryset = PurchaseOrderProof.objects.all()
    serializer_class = PurchaseOrderProofSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['purchase_order', 'status']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return PurchaseOrderProof.objects.none()
        
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return PurchaseOrderProof.objects.filter(
                purchase_order__vendor=vendor
            ).select_related('purchase_order', 'reviewed_by')
        except Vendor.DoesNotExist:
            return PurchaseOrderProof.objects.none()
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Vendor profile not found'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        purchase_order_id = request.data.get('purchase_order_id')
        if not purchase_order_id:
            return Response(
                {'error': 'purchase_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            purchase_order = PurchaseOrder.objects.get(
                id=purchase_order_id,
                vendor=vendor
            )
        except PurchaseOrder.DoesNotExist:
            return Response(
                {'error': 'Purchase order not found or you do not have access'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        proof_image = request.FILES.get('proof_image')
        if not proof_image:
            return Response(
                {'error': 'proof_image file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        description = request.data.get('description', '')
        
        proof = PurchaseOrderProof.objects.create(
            purchase_order=purchase_order,
            proof_image=proof_image,
            description=description,
            status='pending'
        )
        
        serializer = self.get_serializer(proof)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get proof statistics for vendor"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Vendor profile not found'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        proofs = PurchaseOrderProof.objects.filter(
            purchase_order__vendor=vendor
        )
        
        stats = {
            'total_submitted': proofs.count(),
            'pending_review': proofs.filter(status='pending').count(),
            'approved': proofs.filter(status='approved').count(),
            'rejected': proofs.filter(status='rejected').count(),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve proof"""
        proof = self.get_object()
        proof.status = 'approved'
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        return Response({'status': 'success', 'message': 'Proof approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject proof with reason"""
        proof = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proof.status = 'rejected'
        proof.rejection_reason = reason
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        return Response({'status': 'success', 'message': 'Proof rejected'})


class PurchaseOrderIssueViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Issues"""
    queryset = PurchaseOrderIssue.objects.all()
    serializer_class = PurchaseOrderIssueSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'issue_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve issue"""
        issue = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        issue.status = 'resolved'
        issue.resolution_notes = resolution_notes
        issue.resolved_by = request.user
        issue.resolved_at = timezone.now()
        issue.save()
        
        return Response({'status': 'success', 'message': 'Issue resolved'})


class PurchaseOrderNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Notes"""
    queryset = PurchaseOrderNote.objects.all()
    serializer_class = PurchaseOrderNoteSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'category']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def perform_create(self, serializer):
        """Set sender to current user"""
        serializer.save(sender=self.request.user)


class MaterialSubstitutionRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Material Substitution Requests"""
    queryset = MaterialSubstitutionRequest.objects.all()
    serializer_class = MaterialSubstitutionRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve substitution request"""
        sub_request = self.get_object()
        sub_request.status = 'approved'
        sub_request.reviewed_by = request.user
        sub_request.reviewed_at = timezone.now()
        sub_request.save()
        
        return Response({'status': 'success', 'message': 'Substitution request approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject substitution request"""
        sub_request = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sub_request.status = 'rejected'
        sub_request.rejection_reason = reason
        sub_request.reviewed_by = request.user
        sub_request.reviewed_at = timezone.now()
        sub_request.save()
        
        return Response({'status': 'success', 'message': 'Substitution request rejected'})


class VendorSelfInfoViewSet(viewsets.ViewSet):
    """
    ViewSet for Vendor's own information.
    Allows vendors to access and update their own profile data.
    """
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def me(self, request):
        """Get current vendor's info"""
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user, active=True)
            serializer = VendorSerializer(vendor)
            return Response({
                'count': 1,
                'results': [serializer.data]
            })
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'You are not linked to an active vendor profile'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['patch'], permission_classes=[AllowAny])
    def update_me(self, request):
        """Update current vendor's info"""
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user, active=True)
            serializer = VendorSerializer(vendor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Vendor information updated successfully',
                    'results': [serializer.data]
                })
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'You are not linked to an active vendor profile'},
                status=status.HTTP_403_FORBIDDEN
            )


class VendorPerformanceViewSet(viewsets.ViewSet):
    """
    ViewSet for Vendor Performance Analytics.
    Provides performance metrics and scorecard data.
    """
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def scorecard(self, request):
        """Get vendor performance scorecard"""
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response(
                {'error': 'vendor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Vendor not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate QC pass rate for insights
        qc_inspections_90d = QCInspection.objects.filter(
            vendor=vendor,
            created_at__gte=timezone.now() - timedelta(days=90)
        )
        total_qc_90d = qc_inspections_90d.count()
        passed_qc_90d = qc_inspections_90d.filter(status='passed').count()
        qc_pass_rate = (passed_qc_90d / total_qc_90d * 100) if total_qc_90d > 0 else 0
        
        # On-time delivery rate
        stages = JobVendorStage.objects.filter(
            vendor=vendor,
            status='completed',
            completed_at__isnull=False
        )
        total_stages = stages.count()
        # Calculate on-time based on completed_at vs expected_completion
        on_time_stages = stages.filter(completed_at__lte=F('expected_completion')).count()
        on_time_rate = (on_time_stages / total_stages * 100) if total_stages > 0 else 0
        
        # Average turnaround time
        completed_pos = PurchaseOrder.objects.filter(
            vendor=vendor,
            status='completed',
            completed_at__isnull=False
        )
        avg_turnaround = 0
        if completed_pos.exists():
            turnaround_times = [
                (po.completed_at.date() - po.created_at.date()).days
                for po in completed_pos
            ]
            avg_turnaround = sum(turnaround_times) / len(turnaround_times)
        
        # Cost per job
        total_cost = PurchaseOrder.objects.filter(vendor=vendor).aggregate(
            Sum('total_cost')
        )['total_cost__sum'] or 0
        total_jobs = PurchaseOrder.objects.filter(vendor=vendor).count()
        cost_per_job = (total_cost / total_jobs) if total_jobs > 0 else 0
        
        # Defect rate (from QC inspections)
        qc_inspections = QCInspection.objects.filter(vendor=vendor)
        total_qc = qc_inspections.count()
        failed_qc = qc_inspections.filter(status__in=['failed', 'rework']).count()
        defect_rate = (failed_qc / total_qc * 100) if total_qc > 0 else 0
        
        # Additional metrics
        total_pos_offered = PurchaseOrder.objects.filter(vendor=vendor).count()
        accepted_pos = PurchaseOrder.objects.filter(vendor=vendor, vendor_accepted=True).count()
        acceptance_rate = (accepted_pos / total_pos_offered * 100) if total_pos_offered > 0 else 0
        
        # Response time (avg hours to accept PO)
        accepted_pos_with_time = PurchaseOrder.objects.filter(
            vendor=vendor, 
            vendor_accepted=True,
            vendor_accepted_at__isnull=False
        )
        response_times = [
            (po.vendor_accepted_at - po.created_at).total_seconds() / 3600
            for po in accepted_pos_with_time
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Ghosting incidents (POs accepted but no activity for >48hrs)
        ghosting_incidents = PurchaseOrder.objects.filter(
            vendor=vendor,
            vendor_accepted=True,
            updated_at__lt=timezone.now() - timedelta(hours=48),
            status='in_production'
        ).count()
        
        # Decline rate
        declined_pos = PurchaseOrder.objects.filter(vendor=vendor, status='cancelled').count()
        decline_rate = (declined_pos / total_pos_offered * 100) if total_pos_offered > 0 else 0
        
        # Performance insights
        insights = []
        
        if qc_pass_rate >= 95:
            insights.append({
                'type': 'positive',
                'icon': 'check-circle',
                'title': 'Strong QC Track Record',
                'description': f"Maintained {qc_pass_rate:.1f}% QC pass rate over 90 days - {total_qc_90d} inspections"
            })
        
        if on_time_rate < 85:
            insights.append({
                'type': 'warning',
                'icon': 'alert-triangle',
                'title': 'Attention Needed: On-Time Delivery',
                'description': f"On-time rate at {on_time_rate:.1f}% - target is 85%+"
            })
        
        if defect_rate > 5:
            insights.append({
                'type': 'negative',
                'icon': 'x-circle',
                'title': 'Quality Concerns: Too Many Defects',
                'description': f"Defect rate at {defect_rate:.1f}% - {failed_qc} failed out of {total_qc} inspections"
            })
        
        # Build response
        scorecard_data = {
            'overall_score': int(vendor.vps_score_value),
            'vps_grade': vendor.vps_score,
            'tax_status': 'Compliant with tax filing' if vendor.tax_pin else 'No tax info',
            'certifications': ['Certified Vendor'] if vendor.recommended else [],
            
            # Metrics
            'on_time_rate': round(on_time_rate, 1),
            'quality_score': round(qc_pass_rate, 1),
            'avg_turnaround': round(avg_turnaround, 1),
            'defect_rate': round(defect_rate, 1),
            'cost_per_job': round(cost_per_job, 2),
            'acceptance_rate': round(acceptance_rate, 1),
            'response_time': round(avg_response_time, 1),
            'ghosting_incidents': ghosting_incidents,
            'decline_rate': round(decline_rate, 1),
            
            # Insights
            'insights': insights,
        }
        
        serializer = VendorPerformanceSerializer(scorecard_data)
        return Response(serializer.data)


class VendorIssuesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vendor to report and view issues with purchase orders.
    """
    permission_classes = [AllowAny]
    serializer_class = PurchaseOrderIssueSerializer
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return PurchaseOrderIssue.objects.none()
        
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return PurchaseOrderIssue.objects.filter(
                purchase_order__vendor=vendor
            ).select_related('purchase_order').order_by('-created_at')
        except Vendor.DoesNotExist:
            return PurchaseOrderIssue.objects.none()
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        purchase_order_id = request.data.get('purchase_order_id')
        
        try:
            purchase_order = PurchaseOrder.objects.get(
                id=purchase_order_id,
                vendor=vendor
            )
        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        issue = PurchaseOrderIssue.objects.create(
            purchase_order=purchase_order,
            issue_type=request.data.get('issue_type', 'other'),
            description=request.data.get('description', ''),
            status='open'
        )
        
        serializer = self.get_serializer(issue)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MaterialSubstitutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vendors to create and view material substitution requests.
    """
    permission_classes = [AllowAny]
    serializer_class = MaterialSubstitutionRequestSerializer
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return MaterialSubstitutionRequest.objects.none()
        
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return MaterialSubstitutionRequest.objects.filter(
                purchase_order__vendor=vendor
            ).select_related('purchase_order').order_by('-created_at')
        except Vendor.DoesNotExist:
            return MaterialSubstitutionRequest.objects.none()
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        purchase_order_id = request.data.get('purchase_order_id')
        
        try:
            purchase_order = PurchaseOrder.objects.get(
                id=purchase_order_id,
                vendor=vendor
            )
        except PurchaseOrder.DoesNotExist:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        substitution = MaterialSubstitutionRequest.objects.create(
            purchase_order=purchase_order,
            original_material=request.data.get('original_material', ''),
            proposed_material=request.data.get('substitute_material', ''),
            match_percentage=request.data.get('match_percentage', 100),
            justification=request.data.get('reason', ''),
            status='pending'
        )
        
        serializer = self.get_serializer(substitution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VendorActivePurchaseOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to return vendor's active purchase orders for dropdown selections.
    """
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)
        
        try:
            vendor = Vendor.objects.get(user=request.user)
            purchase_orders = PurchaseOrder.objects.filter(
                vendor=vendor,
                status__in=['NEW', 'ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
            ).values('id', 'po_number', 'product_type').order_by('-created_at')
            
            return Response(list(purchase_orders), status=status.HTTP_200_OK)
        except Vendor.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)
