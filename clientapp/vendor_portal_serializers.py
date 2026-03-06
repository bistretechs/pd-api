from rest_framework import serializers
from .models import (
    PurchaseOrder,
    VendorInvoice,
    PurchaseOrderProof,
    PurchaseOrderIssue,
    PurchaseOrderNote,
    MaterialSubstitutionRequest,
    Vendor
)

class PurchaseOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.name')
    job_number = serializers.ReadOnlyField(source='job.job_number')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    milestone_display = serializers.CharField(source='get_milestone_display', read_only=True)
    days_until_due = serializers.ReadOnlyField()
    is_delayed = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class VendorInvoiceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vendor_name = serializers.ReadOnlyField(source='vendor.name')
    po_number = serializers.ReadOnlyField(source='purchase_order.po_number')

    class Meta:
        model = VendorInvoice
        fields = '__all__'
        ref_name = 'VendorInvoiceVendor'

class PurchaseOrderProofSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    proof_type_display = serializers.CharField(source='get_proof_type_display', read_only=True)

    class Meta:
        model = PurchaseOrderProof
        fields = '__all__'
        ref_name = 'PurchaseOrderProofVendor'

class PurchaseOrderIssueSerializer(serializers.ModelSerializer):
    purchase_order = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderIssue
        fields = ['id', 'purchase_order', 'issue_type', 'description', 'status', 'created_at']
        ref_name = 'PurchaseOrderIssueVendor'
    
    def get_purchase_order(self, obj):
        return {
            'id': obj.purchase_order.id,
            'po_number': obj.purchase_order.po_number,
            'product_type': obj.purchase_order.product_type,
        }

class PurchaseOrderNoteSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.get_full_name')
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = PurchaseOrderNote
        fields = '__all__'
        ref_name = 'PurchaseOrderNoteVendor'

class MaterialSubstitutionRequestSerializer(serializers.ModelSerializer):
    purchase_order = serializers.SerializerMethodField()
    cost_difference = serializers.SerializerMethodField()
    cost_impact_percentage = serializers.SerializerMethodField()
    substitute_material = serializers.CharField(source='proposed_material', read_only=True)
    reason = serializers.CharField(source='justification', read_only=True)
    approval_status = serializers.CharField(source='status', read_only=True)
    approval_notes = serializers.SerializerMethodField()
    original_cost = serializers.SerializerMethodField()
    substitute_cost = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = MaterialSubstitutionRequest
        fields = [
            'id', 'purchase_order', 'original_material', 'substitute_material', 
            'reason', 'match_percentage', 'approval_status', 'approval_notes',
            'original_cost', 'substitute_cost',
            'cost_difference', 'cost_impact_percentage',
            'created_at', 'updated_at'
        ]
        ref_name = 'MaterialSubstitutionRequestVendor'
    
    def get_purchase_order(self, obj):
        return {
            'id': obj.purchase_order.id,
            'po_number': obj.purchase_order.po_number,
            'product_type': obj.purchase_order.product_type,
        }
    
    def get_cost_difference(self, obj):
        return 0
    
    def get_cost_impact_percentage(self, obj):
        return 0
    
    def get_approval_notes(self, obj):
        return ""
    
    def get_original_cost(self, obj):
        return 0
    
    def get_substitute_cost(self, obj):
        return 0

class VendorPerformanceSerializer(serializers.Serializer):
    overall_score = serializers.IntegerField()
    vps_grade = serializers.CharField()
    tax_status = serializers.CharField()
    certifications = serializers.ListField(child=serializers.CharField())
    
    # Metrics
    on_time_rate = serializers.FloatField()
    quality_score = serializers.FloatField()
    avg_turnaround = serializers.FloatField()
    defect_rate = serializers.FloatField()
    cost_per_job = serializers.FloatField()
    acceptance_rate = serializers.FloatField()
    response_time = serializers.FloatField()
    ghosting_incidents = serializers.IntegerField()
    decline_rate = serializers.FloatField()
    
    # Insights
    insights = serializers.ListField(child=serializers.DictField())
