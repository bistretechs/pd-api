# clients/urls.py
from django.urls import path
from . import views
from . import admin_crud_operations
from . import ajax_views
from django.urls import reverse
from django.shortcuts import redirect
from django.urls import include
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import admin_views, admin_api

urlpatterns = [
    path('', views.login_redirect, name='login_redirect'),
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Leads
    path('leads/', views.lead_intake, name='lead_intake'),
    path('leads/qualify/<str:lead_id>/', views.qualify_lead, name='qualify_lead'),
    path('leads/convert/<str:lead_id>/', views.convert_lead, name='convert_lead'),
    path('leads/check-duplicate/', views.check_duplicate_lead, name='check_duplicate_lead'),
    
    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/onboarding/', views.client_onboarding, name='client_onboarding'),
    path('clients/<int:pk>/', views.client_profile, name='client_profile'),
    path('clients/<int:pk>/edit/', views.edit_client, name='edit_client'),
    path('clients/<int:pk>/edit/', views.edit_client, name='edit_client'),
    
    # Quotes
    path('am/quotes/create/', views.create_quote, name='create_quote'),
    # path('quotes/', views.quotes_list, name='quotes_list'),
    path('quotes/<str:quote_id>/', views.quote_detail, name='quote_detail'),
    path('quotes/<str:quote_id>/update-status/', views.update_quote_status, name='update_quote_status'),
    path('quotes/<str:quote_id>/delete/', views.delete_quote, name='delete_quote'),
    path('production/quotes/<str:quote_id>/cost/', views.update_quote_costing, name='production_quote_costing'),
    
    # API endpoints for quotes
    path('api/client/<int:client_id>/', views.get_client_details, name='get_client_details'),
    path('api/lead/<int:lead_id>/', views.get_lead_details, name='get_lead_details'),
    path('api/quotes/save-draft/', views.save_quote_draft, name='save_quote_draft'),
    
    # Jobs
    path('jobs/create/', views.create_job, name='create_job'),
    
    # Job Detail & Management
    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    path('job/<int:pk>/add-note/', views.add_job_note, name='add_job_note'),
    path('job/<int:pk>/upload-file/', views.upload_job_file, name='upload_job_file'),
    path('job/<int:pk>/update-progress/', views.update_job_progress, name='update_job_progress'),
    path('job/<int:pk>/add-stage/', views.add_vendor_stage, name='add_vendor_stage'),
    
    # QC Inspection Start (placeholder if doesn't exist)
    path('qc-inspection/start/<int:job_id>/', views.qc_inspection_start, name='qc_inspection_start'),
    
    path('account-manager/quotes/', views.quote_management, name='quote_management'),
    path('account-manager/quotes/create/', views.create_multi_quote, name='create_multi_quote'),
    path('account-manager/catalog/', views.product_catalog, name='product_catalog'),
    path('account-manager/analytics/', views.analytics, name='analytics'),
    path('account-manager/base/', views.base_view, name='base_view'),
    path('account-manager/jobs/', views.account_manager_jobs_list, name='account_manager_jobs_list'),
    path('account-manager/jobs/board/', views.job_assignment_board, name='job_assignment_board'),
    path('account-manager/job/<int:pk>/', views.account_manager_job_detail, name='account_manager_job_detail'),
    path('account-manager/job/<int:pk>/update/', views.account_manager_job_update, name='account_manager_job_update'),
    path('account-manager/job/<int:pk>/remind/', views.account_manager_send_reminder, name='account_manager_send_reminder'),
    path('account-manager/substitutions/', views.substitution_dashboard, name='substitution_dashboard'),
    
    # Job Interaction APIs (AJAX endpoints for AM portal)
    path('api/job/<int:job_id>/assign/', views.api_assign_job, name='api_assign_job'),
    path('api/job/<int:job_id>/remind/', views.api_send_job_reminder, name='api_send_job_reminder'),
    path('api/job/<int:job_id>/message/', views.api_send_job_message, name='api_send_job_message'),
    path('api/job/<int:job_id>/details/', views.api_get_job_details, name='api_get_job_details'),
    path('api/job/<int:job_id>/messages/', views.api_get_job_messages, name='api_get_job_messages'),
    path('api/job/<int:job_id>/progress/', views.api_job_progress, name='api_job_progress'),
    path('api/production-users/', views.api_get_production_users, name='api_get_production_users'),
    
    path('quotes/<str:quote_id>/send/', views.send_quote, name='send_quote'),

    # ===== Production Team URLs =====
    path('production/quotes/', views.quote_review_queue, name='production_quote_review'),
    # Add this to your urlpatterns in clientapp/urls.py
   path('production/quotes/<str:quote_id>/cost-v2/', views.update_quote_costing_v2, name='production_quote_costing_v2'),
    path('production/catalog/', views.production_catalog, name='production_catalog'),
    # path('production/catalog/', views.product_detail, name='product_detail'),
    path('production/dashboard/', views.production2_dashboard, name='production2_dashboard'),
    path('production/jobs2/', views.jobs2_list, name='jobs2_list'),
    path('production/invoices2/', views.invoices2_list, name='invoices2_list'),
    path('production/proofs2/', views.proofs2_list, name='proofs2_list'),
    path('production/messages2/', views.messages2_list, name='messages2_list'),
    path('production/vendors2/', views.vendors2_list, name='vendors2_list'),
    path('production/analytics/', views.production_analytics, name='production_analytics'),
    
    # ✅ NEW: Production Team Dashboard (Gap 6.1)
    path('pt-dashboard/', views.production_team_dashboard, name='production_team_dashboard'),
    path('api/vendor/<int:vendor_id>/workload/', views.get_vendor_workload, name='get_vendor_workload'),
    
    # ✅ NEW: Job Assignment UI (Gap 10)
    path('production/jobs/assign/', views.production_job_assignment, name='production_job_assignment'),
    path('production/jobs/assign/submit/', views.production_job_assignment_submit, name='production_job_assignment_submit'),
    
    # ✅ NEW: Invoice Approval UI (Gap 11)
    path('production/invoices/approve/', views.production_invoice_approval, name='production_invoice_approval'),
    path('production/invoices/approve/submit/', views.production_invoice_approval_submit, name='production_invoice_approval_submit'),
    
    # ✅ NEW: Proof Approval Workflow (Gap 12)
    path('production/proofs/approve/', views.production_proof_approval, name='production_proof_approval'),
    path('production/proofs/approve/submit/', views.production_proof_approval_submit, name='production_proof_approval_submit'),
    
    # ✅ NEW: Vendor Progress Submit (Gap 7)
    path('vendor/progress/submit/', views.vendor_progress_submit, name='vendor_progress_submit'),
    
    # ✅ NEW: Backend Gaps - API Endpoints
    # Vendor Capacity Alerts
    path('api/alerts/', views.VendorCapacityAlertViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_alerts_list'),
    path('api/alerts/<int:pk>/', views.VendorCapacityAlertViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_alert_detail'),
    path('api/alerts/<int:pk>/acknowledge/', views.VendorCapacityAlertViewSet.as_view({'post': 'acknowledge'}), name='api_alert_acknowledge'),
    path('api/alerts/<int:pk>/resolve/', views.VendorCapacityAlertViewSet.as_view({'post': 'resolve'}), name='api_alert_resolve'),
    path('api/alerts/check-capacity/', views.VendorCapacityAlertViewSet.as_view({'post': 'check_capacity'}), name='api_check_capacity'),
    
    # Purchase Order Milestones
    path('api/milestones/', views.POSMilestoneViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_milestones_list'),
    path('api/milestones/<int:pk>/', views.POSMilestoneViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_milestone_detail'),
    path('api/milestones/<int:pk>/complete/', views.POSMilestoneViewSet.as_view({'post': 'complete'}), name='api_milestone_complete'),
    path('api/milestones/check-approaching/', views.POSMilestoneViewSet.as_view({'post': 'check_approaching'}), name='api_check_approaching'),
    
    # Material Substitution Approvals
    path('api/substitutions/', views.MaterialSubstitutionApprovalViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_substitutions_list'),
    path('api/substitutions/<int:pk>/', views.MaterialSubstitutionApprovalViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_substitution_detail'),
    path('api/substitutions/<int:pk>/approve/', views.MaterialSubstitutionApprovalViewSet.as_view({'post': 'approve'}), name='api_substitution_approve'),
    path('api/substitutions/<int:pk>/reject/', views.MaterialSubstitutionApprovalViewSet.as_view({'post': 'reject'}), name='api_substitution_reject'),
    path('api/substitutions/<int:pk>/cost-impact/', views.MaterialSubstitutionApprovalViewSet.as_view({'get': 'cost_impact'}), name='api_substitution_cost_impact'),
    
    # Invoice Holds
    path('api/invoice-holds/', views.InvoiceHoldViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_invoice_holds_list'),
    path('api/invoice-holds/<int:pk>/', views.InvoiceHoldViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_invoice_hold_detail'),
    path('api/invoice-holds/hold-invoice/', views.InvoiceHoldViewSet.as_view({'post': 'hold_invoice'}), name='api_hold_invoice'),
    path('api/invoice-holds/<int:pk>/release/', views.InvoiceHoldViewSet.as_view({'post': 'release'}), name='api_release_hold'),
    
    # PT Dashboard (Phase 2)
    path('api/pt-dashboard/overview/', views.PTDashboardViewSet.as_view({'get': 'overview'}), name='api_pt_dashboard_overview'),
    path('api/pt-dashboard/vendor-status/', views.PTDashboardViewSet.as_view({'get': 'vendor_status'}), name='api_vendor_status'),
    
    # SLA Escalations (Phase 2)
    path('api/sla-escalations/', views.SLAEscalationViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_sla_escalations_list'),
    path('api/sla-escalations/<int:pk>/', views.SLAEscalationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_sla_escalation_detail'),
    path('api/sla-escalations/escalate-job/', views.SLAEscalationViewSet.as_view({'post': 'escalate_job'}), name='api_escalate_job'),
    path('api/sla-escalations/<int:pk>/notify-vendor/', views.SLAEscalationViewSet.as_view({'post': 'notify_vendor'}), name='api_notify_vendor_escalation'),
    path('api/sla-escalations/<int:pk>/notify-pt/', views.SLAEscalationViewSet.as_view({'post': 'notify_pt'}), name='api_notify_pt_escalation'),
    path('api/sla-escalations/<int:pk>/escalate-level/', views.SLAEscalationViewSet.as_view({'post': 'escalate_level'}), name='api_escalate_level'),
    path('api/sla-escalations/<int:pk>/resolve/', views.SLAEscalationViewSet.as_view({'post': 'resolve'}), name='api_resolve_escalation'),
    path('api/sla-escalations/pending/', views.SLAEscalationViewSet.as_view({'get': 'pending'}), name='api_pending_escalations'),
    path('api/sla-escalations/critical/', views.SLAEscalationViewSet.as_view({'get': 'critical'}), name='api_critical_escalations'),
    path('api/sla-escalations/check-and-escalate/', views.SLAEscalationViewSet.as_view({'post': 'check_and_escalate'}), name='api_check_and_escalate'),
    
    # Progress Updates (Task 7)
    path('api/progress-updates/', views.ProgressUpdateBatchViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_progress_updates_list'),
    path('api/progress-updates/<int:pk>/', views.ProgressUpdateBatchViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_progress_update_detail'),
    path('api/progress-updates/submit-update/', views.ProgressUpdateBatchViewSet.as_view({'post': 'submit_update'}), name='api_submit_progress_update'),
    path('api/progress-updates/latest/', views.ProgressUpdateBatchViewSet.as_view({'get': 'latest_by_po'}), name='api_latest_progress_update'),
    
    # QC-Proof Links (Task 9 - QC-Proof Integration)
    path('api/qc-proof-links/', views.QCProofLinkViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_qc_proof_links_list'),
    path('api/qc-proof-links/<int:pk>/', views.QCProofLinkViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_qc_proof_link_detail'),
    path('api/qc-proof-links/link-qc-to-proof/', views.QCProofLinkViewSet.as_view({'post': 'link_qc_to_proof'}), name='api_link_qc_to_proof'),
    path('api/qc-proof-links/<int:pk>/calculate-vps-impact/', views.QCProofLinkViewSet.as_view({'post': 'calculate_vps_impact'}), name='api_calculate_vps_impact'),
    
    # VPS Recalculation (Task 11 - VPS Recalculation on QC Fail)
    path('api/vps-recalculation/', views.VPSRecalculationViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_vps_recalculation_list'),
    path('api/vps-recalculation/<int:pk>/', views.VPSRecalculationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_vps_recalculation_detail'),
    path('api/vps-recalculation/recalculate-vendor/', views.VPSRecalculationViewSet.as_view({'post': 'recalculate_vendor_vps'}), name='api_recalculate_vendor_vps'),
    
    # Customer Notifications (Task 10 - Substitution Customer Notification)
    path('api/customer-notifications/', views.CustomerNotificationViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_customer_notifications_list'),
    path('api/customer-notifications/<int:pk>/', views.CustomerNotificationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_customer_notification_detail'),
    path('api/customer-notifications/send-notification/', views.CustomerNotificationViewSet.as_view({'post': 'send_notification'}), name='api_send_customer_notification'),
    path('api/customer-notifications/<int:pk>/mark-acknowledged/', views.CustomerNotificationViewSet.as_view({'post': 'mark_acknowledged'}), name='api_mark_notification_acknowledged'),
    
    # Material Substitutions API
    path('api/material-substitutions/request/', views.api_create_substitution_request, name='api_create_substitution_request'),
    path('api/material-substitutions/<int:pk>/', views.api_get_substitution_request, name='api_get_substitution_request'),
    path('api/material-substitutions/<int:pk>/approve/', views.api_approve_substitution, name='api_approve_substitution'),
    path('api/material-substitutions/<int:pk>/reject/', views.api_reject_substitution, name='api_reject_substitution'),
    path('api/material-substitutions/<int:pk>/comments/', views.api_get_substitution_comments, name='api_get_substitution_comments'),
    path('api/material-substitutions/<int:pk>/comment/', views.api_add_substitution_comment, name='api_add_substitution_comment'),
    path('api/purchase-orders/<int:pk>/', views.api_get_purchase_order_details, name='api_get_purchase_order_details'),
    
    # Deadline Calculations (Task 8 - Automatic Deadline Calculation)
    path('api/deadline-calculations/', views.DeadlineCalculationViewSet.as_view({'get': 'list', 'post': 'create'}), name='api_deadline_calculations_list'),
    path('api/deadline-calculations/<int:pk>/', views.DeadlineCalculationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api_deadline_calculation_detail'),
    path('api/deadline-calculations/calculate-deadline/', views.DeadlineCalculationViewSet.as_view({'post': 'calculate_deadline'}), name='api_calculate_deadline'),
    
    path('notifications/', views.notifications, name='notifications'),
    
    path('base2/', views.base_view, name='base_view'),

    # Global search
    path('search/', views.search, name='search'),

    path('login-redirect/', views.login_redirect, name='login_redirect'),
    # Finance (restricted to Finance group)
    
    path('update-quote-status/', views.update_quote_status, name='update_quote_status'),
    path('production/jobs/', views.production_jobs, name='production_jobs'),
    # Product Image AJAX endpoints
 path('ajax/product-image/<int:image_id>/', ajax_views.ajax_get_product_image, name='ajax_get_product_image'),
 path('ajax/product-image/<int:image_id>/update/', ajax_views.ajax_update_product_image, name='ajax_update_product_image'),
 path('ajax/product-image/<int:image_id>/delete/', ajax_views.ajax_delete_product_image, name='ajax_delete_product_image'),
 path('ajax/product-image/<int:image_id>/replace/', ajax_views.ajax_replace_product_image, name='ajax_replace_product_image'),
    

    
    # Finance Dashboard
   
    # path('analytics_production/', views.analytics_dashboard, name='analytics_dashboard'),
    # path('dashboard/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # Product Catalog 
    path('production/catalog/', views.production_catalog, name='production_catalog'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('production/products/create/', views.product_create, name='product_create'),
    path('production/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('production/products/<int:product_pk>/images/<int:image_pk>/delete/', 
         views.product_delete_image, name='product_delete_image'),
    path('production/products/images/<int:image_pk>/update/', 
         views.product_update_image_metadata, name='product_update_image_metadata'),
    path('production/products/calculate-pricing/', 
         views.calculate_pricing, name='calculate_pricing'),
      path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('my-quotes/', views.my_quotes, name='my_quotes'),
    path('quote-detail/<str:quote_id>/', views.quote_detail2, name='quote_detail2'),

    path('quotes/<str:quote_id>/action/', views.quote_action, name='quote_action'),
    # Multi-Product Quotes
    path('quotes/', views.quotes_list, name='quotes_list'),
    # path('quotes/create/', views.create_quote, name='create_quote'),
    path('create/quote', views.quote_create, name='quote_create'),
    path('quotes/<str:quote_id>/download/', views.download_quote_pdf, name='download_quote_pdf'),
    path('quotes/<str:quote_id>/clone/', views.clone_quote, name='clone_quote'),
    path('quotes/<str:quote_id>/convert-to-job/', views.convert_quote_to_job, name='convert_quote_to_job'),
    # path('quotes/<str:quote_id>/', views.quote_detail, name='quote_detail'),
    # path('quotes/<str:quote_id>/edit/', views.quote_edit, name='quote_edit'),
    
    # Self-Quote Interface (Customer-facing)
    path('self-quote/', views.self_quote, name='self_quote'),
     path('api/product-price/<int:product_id>/', views.get_product_price, name='get_product_price'),
     path('api/product-catalog/', views.api_product_catalog, name='api_product_catalog'),
    
    # API endpoints for AJAX operations
    # path('api/products/search/', views.api_product_search, name='api_product_search'),
    # path('api/quotes/<str:quote_id>/add-item/', views.api_quote_add_item, name='api_quote_add_item'),
    # path('api/quotes/<str:quote_id>/remove-item/', views.api_quote_remove_item, name='api_quote_remove_item'),
    # path('api/quotes/<str:quote_id>/calculate/', views.api_quote_calculate, name='api_quote_calculate'),
     # Quote Sending & Approval
    # path('quotes/<str:quote_id>/send/', views.send_quote, name='send_quote'),
    path('quotes/approve/<str:token>/', views.quote_approval, name='quote_approval'),
    path('quotes/<str:quote_id>/approve/', views.handle_quote_approval, name='handle_quote_approval'),
    # LPO Management
    path('lpo/', views.lpo_list, name='lpo_list'),
    path('lpo/<str:lpo_number>/', views.lpo_detail, name='lpo_detail'),
    path('lpo/<str:lpo_number>/sync/', views.sync_to_quickbooks, name='sync_to_quickbooks'),
    

    path('vendor-comparison/<int:job_id>/', views.vendor_comparison, name='vendor_comparison'),
    path('ajax/create-vendor/', views.ajax_create_vendor, name='ajax_create_vendor'),
    path('vendors/<int:vendor_id>/', views.vendor_profile, name='vendor_profile'),
    # Quality control inspection page
    path('qc-inspection/<int:inspection_id>/', views.qc_inspection, name='qc_inspection'),
    path('vendors/', views.vendor_list, name='vendor_list'),
path('quality-control/', views.quality_control_list, name='quality_control_list'),
    # AJAX endpoints
    path('api/select-vendor/', views.select_vendor, name='select_vendor'),
    path('api/submit-qc/', views.submit_qc, name='submit_qc'),
    path('api/vendors/create/', views.ajax_create_vendor, name='ajax_create_vendor'),
    path('processes/', views.process_list, name='process_list'),
    path('processes/create/', views.process_create, name='process_create'),
    path('processes/<str:process_id>/', views.process_detail, name='process_detail'),
    path('processes/<str:process_id>/edit/', views.process_edit, name='process_edit'),
    # Variable Ranges Management
    path('processes/<str:process_id>/variable-ranges/', views.process_variable_ranges_manager, name='process_variable_ranges_manager'),
    path('ajax/process-variable-ranges/<str:process_id>/add/', views.add_variable_range, name='add_variable_range'),
    path('ajax/process-variable-ranges/<str:process_id>/delete/', views.delete_variable_range, name='delete_variable_range'),
    path('ajax/process-variable-ranges/<int:process_id>/create-samples/', views.create_sample_ranges, name='create_sample_ranges'),
    # path('processes/<str:process_id>/', views.process_detail, name='process_detail'),
    
    # AJAX endpoints
    path('ajax/generate-process-id/', views.ajax_generate_process_id, name='ajax_generate_process_id'),
    path('ajax/calculate-margin/', views.ajax_calculate_margin, name='ajax_calculate_margin'),
    path('ajax/delete-process/<int:process_id>/', views.ajax_delete_process, name='ajax_delete_process'),
    path('delivery/', views.delivery_list, name='delivery_list'),
    # Job Completion
    # path('jobs/<int:pk>/complete/', views.complete_job, name='complete_job'),
    
    # Lead Conversion
    # path('leads/<str:lead_id>/convert-to-client/', views.convert_lead_to_client, name='convert_lead_to_client'),
    
    # Live Data API
    # path('api/dashboard/data/', views.get_dashboard_data, name='get_dashboard_data'),
    # path('api/notifications/', views.get_notifications, name='get_notifications'),
    # path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
        # Admin Dashboard AJAX Endpoints
    path('admin/dismiss-alert/<int:alert_id>/', views.dismiss_alert, name='dismiss_alert'),
    path('admin/export-report/<str:report_type>/', views.export_dashboard_report, name='export_report'),
    
    # Process-Product Integration AJAX endpoints
    path('ajax/process/<int:process_id>/tiers/', ajax_views.ajax_process_tiers, name='ajax_process_tiers'),
    path('ajax/process/<int:process_id>/variables/', ajax_views.ajax_process_variables, name='ajax_process_variables'),
    path('ajax/process/<int:process_id>/calculate/', ajax_views.ajax_calculate_pricing, name='ajax_calculate_pricing'),

    # Add these to your urlpatterns
path('qc-inspection/<int:inspection_id>/', views.qc_inspection, name='qc_inspection'),
path('api/submit-qc/', views.submit_qc, name='submit_qc'),
path('delivery/handoff/<int:job_id>/', views.delivery_handoff, name='delivery_handoff'),
    path('api/submit-delivery-handoff/', views.submit_delivery_handoff, name='submit_delivery_handoff'),
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('job/<int:pk>/mark-completed/', views.complete_job, name='mark_job_completed'),
    path('production/settings/', views.production_settings, name='production_settings'),
    path('admin-dashboard/', views.admin_dashboard_index, name='admin_dashboard_index'),
    # OLD ROUTES - now using admin_crud_operations below
    # path('admin-dashboard/clients/', views.admin_clients_list, name='admin_clients_list'),
    # path('admin-dashboard/quotes/', views.admin_quotes_list, name='admin_quotes_list'),
    # path('admin-dashboard/jobs/', views.admin_jobs_list, name='admin_jobs_list'),
    # path('admin-dashboard/products/', views.admin_products_list, name='admin_products_list'),
    # path('admin-dashboard/vendors/', views.admin_vendors_list, name='admin_vendors_list'),
    # path('admin-dashboard/leads/', views.admin_leads_list, name='admin_leads_list'),
    # path('admin-dashboard/processes/', views.admin_processes_list, name='admin_processes_list'),
    # path('admin-dashboard/qc/', views.admin_qc_list, name='admin_qc_list'),
    # path('admin-dashboard/deliveries/', views.admin_deliveries_list, name='admin_deliveries_list'),
    # path('admin-dashboard/lpos/', views.admin_lpos_list, name='admin_lpos_list'),
    # path('admin-dashboard/payments/', views.admin_payments_list, name='admin_payments_list'),
    path('admin-dashboard/analytics/', views.admin_analytics, name='admin_analytics'),
    # path('admin-dashboard/users/', views.admin_users_list, name='admin_users_list'),  # Disabled - using admin_crud_operations version
    path('admin-dashboard/settings/', views.admin_settings, name='admin_settings'),
    path('admin-dashboard/alerts/', views.admin_alerts_list, name='admin_alerts_list'),
    
    # ===== ADMIN DASHBOARD CRUD ROUTES (Django Admin Style) =====
    path('admin-dashboard/bulk-action/', admin_crud_operations.admin_bulk_action, name='admin_bulk_action'),
    # Clients CRUD
    path('admin-dashboard/clients/', admin_crud_operations.admin_clients_list, name='admin_clients_list'),
    path('admin-dashboard/clients/add/', admin_crud_operations.admin_client_add, name='admin_client_add'),
    path('admin-dashboard/clients/<int:pk>/', admin_crud_operations.admin_client_detail, name='admin_client_detail'),
    path('admin-dashboard/clients/<int:pk>/delete/', admin_crud_operations.admin_client_delete, name='admin_client_delete'),
    
    # Leads CRUD
    path('admin-dashboard/leads/', admin_crud_operations.admin_leads_list, name='admin_leads_list'),
    path('admin-dashboard/leads/add/', admin_crud_operations.admin_lead_add, name='admin_lead_add'),
    path('admin-dashboard/leads/<int:pk>/', admin_crud_operations.admin_lead_detail, name='admin_lead_detail'),
    path('admin-dashboard/leads/<int:pk>/delete/', admin_crud_operations.admin_lead_delete, name='admin_lead_delete'),
    
    # Quotes CRUD
    path('admin-dashboard/quotes/', admin_crud_operations.admin_quotes_list, name='admin_quotes_list'),
    path('admin-dashboard/quotes/add/', admin_crud_operations.admin_quote_add, name='admin_quote_add'),
    path('admin-dashboard/quotes/<int:pk>/', admin_crud_operations.admin_quote_detail, name='admin_quote_detail'),
    path('admin-dashboard/quotes/<int:pk>/delete/', admin_crud_operations.admin_quote_delete, name='admin_quote_delete'),
    
    # Products CRUD
    path('admin-dashboard/products/', admin_crud_operations.admin_products_list, name='admin_products_list'),
    path('admin-dashboard/products/add/', admin_crud_operations.admin_product_add, name='admin_product_add'),
    path('admin-dashboard/products/<int:pk>/', admin_crud_operations.admin_product_detail, name='admin_product_detail'),
    path('admin-dashboard/products/<int:pk>/delete/', admin_crud_operations.admin_product_delete, name='admin_product_delete'),
    
    # Jobs CRUD
    path('admin-dashboard/jobs/', admin_crud_operations.admin_jobs_list, name='admin_jobs_list'),
    path('admin-dashboard/jobs/add/', admin_crud_operations.admin_job_add, name='admin_job_add'),
    path('admin-dashboard/jobs/<int:pk>/', admin_crud_operations.admin_job_detail, name='admin_job_detail'),
    path('admin-dashboard/jobs/<int:pk>/delete/', admin_crud_operations.admin_job_delete, name='admin_job_delete'),
    
    # Vendors CRUD
    path('admin-dashboard/vendors/', admin_crud_operations.admin_vendors_list, name='admin_vendors_list'),
    path('admin-dashboard/vendors/add/', admin_crud_operations.admin_vendor_add, name='admin_vendor_add'),
    path('admin-dashboard/vendors/<int:pk>/', admin_crud_operations.admin_vendor_detail, name='admin_vendor_detail'),
    path('admin-dashboard/vendors/<int:pk>/delete/', admin_crud_operations.admin_vendor_delete, name='admin_vendor_delete'),
    
    # Processes CRUD
    path('admin-dashboard/processes/', admin_crud_operations.admin_processes_list, name='admin_processes_list'),
    path('admin-dashboard/processes/add/', admin_crud_operations.admin_process_add, name='admin_process_add'),
    path('admin-dashboard/processes/<int:pk>/', admin_crud_operations.admin_process_detail, name='admin_process_detail'),
    path('admin-dashboard/processes/<int:pk>/delete/', admin_crud_operations.admin_process_delete, name='admin_process_delete'),
    
    # LPOs CRUD
    path('admin-dashboard/lpos/', admin_crud_operations.admin_lpos_list, name='admin_lpos_list'),
    path('admin-dashboard/lpos/add/', admin_crud_operations.admin_lpo_add, name='admin_lpo_add'),
    path('admin-dashboard/lpos/<int:pk>/', admin_crud_operations.admin_lpo_detail, name='admin_lpo_detail'),
    path('admin-dashboard/lpos/<int:pk>/delete/', admin_crud_operations.admin_lpo_delete, name='admin_lpo_delete'),
    
    # Payments CRUD
    path('admin-dashboard/payments/', admin_crud_operations.admin_payments_list, name='admin_payments_list'),
    path('admin-dashboard/payments/add/', admin_crud_operations.admin_payment_add, name='admin_payment_add'),
    path('admin-dashboard/payments/<int:pk>/', admin_crud_operations.admin_payment_detail, name='admin_payment_detail'),
    path('admin-dashboard/payments/<int:pk>/delete/', admin_crud_operations.admin_payment_delete, name='admin_payment_delete'),
    
    # Users CRUD
    path('admin-dashboard/users/', admin_crud_operations.admin_users_list, name='admin_users_list'),
    path('admin-dashboard/users/add/', admin_crud_operations.admin_user_add, name='admin_user_add'),
    path('admin-dashboard/users/<int:pk>/', admin_crud_operations.admin_user_detail, name='admin_user_detail'),
    path('admin-dashboard/users/<int:pk>/delete/', admin_crud_operations.admin_user_delete, name='admin_user_delete'),
    
    # Groups CRUD (Roles)
    path('admin-dashboard/groups/', admin_crud_operations.admin_groups_list, name='admin_groups_list'),
    path('admin-dashboard/groups/add/', admin_crud_operations.admin_group_add, name='admin_group_add'),
    path('admin-dashboard/groups/<int:pk>/', admin_crud_operations.admin_group_detail, name='admin_group_detail'),
    path('admin-dashboard/groups/<int:pk>/delete/', admin_crud_operations.admin_group_delete, name='admin_group_delete'),
    
    # View-Only Lists
    path('admin-dashboard/qc/', admin_crud_operations.admin_qc_list, name='admin_qc_list'),
    path('admin-dashboard/deliveries/', admin_crud_operations.admin_deliveries_list, name='admin_deliveries_list'),
    path('admin-dashboard/alerts/', admin_crud_operations.admin_alerts_list, name='admin_alerts_list'),
    path('admin-dashboard/audit-logs/', admin_crud_operations.admin_audit_logs, name='admin_audit_logs'),
    

    path('production/settings/', views.production_settings, name='production_settings'),
    path('production/analytics/', views.production_analytics, name='production_analytics'),
    # OLD ROUTES BELOW (DISABLED - using admin_crud_operations instead)
    # ===== ADMIN DASHBOARD ROUTES (Django Admin Style) =====
    # Main dashboard
    # path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Business section
    # path('admin-dashboard/clients/', views.clients_list, name='admin_clients_list'),
    # path('admin-dashboard/leads/', views.leads_list, name='admin_leads_list'),
    # path('admin-dashboard/quotes/', views.quotes_list, name='admin_quotes_list'),
    # path('admin-dashboard/products/', views.products_list, name='admin_products_list'),
    
    # Operations section
    # path('admin-dashboard/jobs/', views.jobs_list, name='admin_jobs_list'),
    # path('admin-dashboard/vendors/', views.vendors_list, name='admin_vendors_list'),
    # path('admin-dashboard/processes/', views.processes_list, name='admin_processes_list'),
    # path('admin-dashboard/qc/', views.qc_list, name='admin_qc_list'),
    # path('admin-dashboard/deliveries/', views.deliveries_list, name='admin_deliveries_list'),
    
    # Financial section
    # path('admin-dashboard/lpos/', views.lpos_list, name='admin_lpos_list'),
    # path('admin-dashboard/payments/', views.payments_list, name='admin_payments_list'),
    # path('admin-dashboard/analytics/', views.analytics_view, name='admin_analytics'),
    
    # System section
    # path('admin-dashboard/users/', views.users_list, name='admin_users_list'),
    
    # AJAX CRUD endpoints (DISABLED - using admin_crud_operations instead)
    # path('api/admin/detail/<str:model_name>/<int:object_id>/', views.get_object_detail, name='api_admin_detail'),
    # path('api/admin/create/<str:model_name>/', views.create_object, name='api_admin_create'),
    # path('api/admin/update/<str:model_name>/<int:object_id>/', views.update_object, name='api_admin_update'),
    # path('api/admin/delete/<str:model_name>/<int:object_id>/', views.delete_object, name='api_admin_delete'),
    
    # Legacy API routes (DISABLED)
    # path('api/admin/clients/create/', views.api_admin_create_client, name='api_admin_create_client'),
    # path('api/admin/clients/<int:client_id>/get/', views.api_admin_get_client, name='api_admin_get_client'),
    # path('api/admin/clients/<int:client_id>/update/', views.api_admin_update_client, name='api_admin_update_client'),
    path('api/admin/clients/<int:client_id>/delete/', views.api_admin_delete_client, name='api_admin_delete_client'),
    
    # Leads CRUD APIs - SPECIFIC FIRST
    path('api/admin/leads/create/', views.api_admin_create_lead, name='api_admin_create_lead'),
    path('api/admin/leads/<int:lead_id>/get/', views.api_admin_get_lead, name='api_admin_get_lead'),
    path('api/admin/leads/<int:lead_id>/update/', views.api_admin_update_lead, name='api_admin_update_lead'),
    path('api/admin/leads/<int:lead_id>/delete/', views.api_admin_delete_lead, name='api_admin_delete_lead'),
    
    # Quotes CRUD APIs - SPECIFIC FIRST
    path('api/admin/quotes/create/', views.api_admin_create_quote, name='api_admin_create_quote'),
    path('api/admin/quotes/<int:quote_id>/get/', views.api_admin_get_quote, name='api_admin_get_quote'),
    path('api/admin/quotes/<int:quote_id>/update/', views.api_admin_update_quote, name='api_admin_update_quote'),
    path('api/admin/quotes/<int:quote_id>/delete/', views.api_admin_delete_quote, name='api_admin_delete_quote'),
    
    # Products CRUD APIs - SPECIFIC FIRST (BEFORE generic /api/admin/products/)
    path('api/admin/products/create/', views.api_admin_create_product, name='api_admin_create_product'),
    path('api/admin/products/<int:product_id>/get/', views.api_admin_get_product, name='api_admin_get_product'),
    path('api/admin/products/<int:product_id>/update/', views.api_admin_update_product, name='api_admin_update_product'),
    path('api/admin/products/<int:product_id>/delete/', views.api_admin_delete_product, name='api_admin_delete_product'),
    
    # Generic list endpoints - AFTER specific routes
    path('api/admin/leads/', views.api_admin_leads, name='api_admin_leads'),
    path('api/admin/leads/<int:lead_id>/', views.api_admin_lead_detail, name='api_admin_lead_detail'),
    path('api/admin/products/', views.api_admin_products, name='api_admin_products'),
    path('api/admin/products/<int:product_id>/', views.api_admin_product_detail, name='api_admin_product_detail'),
    
    # ==================== PAYMENTS ====================
    # path('payments/', admin_views.admin_payments_list, name='admin_payments_list'),
    # path('payments/add/', admin_views.admin_payment_add, name='admin_payment_add'),
    # path('payments/<int:pk>/', admin_views.admin_payment_detail, name='admin_payment_detail'),
    # path('payments/<int:pk>/delete/', admin_views.admin_payment_delete, name='admin_payment_delete'),
    
    # Payment API endpoints
    path('api/payments/', admin_api.api_admin_payments, name='api_admin_payments'),
    
    # ==================== QC INSPECTIONS ====================
    # path('qc/', admin_views.admin_qc_list, name='admin_qc_list'),
    
    # QC API endpoints
    path('api/qc/', admin_api.api_admin_qc_inspections, name='api_admin_qc_inspections'),
    path('api/product-price/<int:product_id>/', views.get_product_price, name='get_product_price'),
    path('api/product-catalog/', views.api_product_catalog, name='api_product_catalog'),
    # ==================== DELIVERIES ====================
    # path('deliveries/', admin_views.admin_deliveries_list, name='admin_deliveries_list'),
    
    # Delivery API endpoints
    # path('api/deliveries/', admin_api.api_admin_deliveries, name='api_admin_deliveries'),
    
    # ==================== USERS ====================
    # path('users/', admin_views.admin_users_list, name='admin_users_list'),
    # path('users/add/', admin_views.admin_user_add, name='admin_user_add'),
    # path('users/<int:pk>/', admin_views.admin_user_detail, name='admin_user_detail'),
    # path('users/<int:pk>/delete/', admin_views.admin_user_delete, name='admin_user_delete'),
    
    # User API endpoints
    path('api/users/create/', admin_api.api_admin_create_user, name='api_admin_create_user'),
    path('api/users/<int:user_id>/', admin_api.api_admin_get_user, name='api_admin_get_user'),
    path('api/users/<int:user_id>/update/', admin_api.api_admin_update_user, name='api_admin_update_user'),
    path('api/users/<int:user_id>/delete/', admin_api.api_admin_delete_user, name='api_admin_delete_user'),
     path('admin-dashboard/activity/', views.admin_activity_list, name='admin_activity_list'),
    
    # ==================== ALERTS ====================
    # path('alerts/', admin_views.admin_alerts_list, name='admin_alerts_list'),
    
    # ==================== CLIENT PORTAL ====================
    # Client Portal URLs - Main SPA Entry Point
    path('client-portal/', views.client_portal_spa, name='client_portal'),
    
    # ==================== VENDOR PORTAL ====================
    # Vendor Portal URLs - Main SPA Entry Point
    path('vendor/', views.vendor_portal_spa, name='vendor_portal'),
    path('vendor/invite/<str:token>/', views.vendor_invite_accept, name='vendor_invite_accept'),
    
    # Individual vendor endpoints (backward compatibility)
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    
    # Invoice Management (Vendor)
    path('vendor/invoices/', views.vendor_invoices, name='vendor_invoices'),
    path('vendor/invoices/create/', views.vendor_create_invoice, name='vendor_create_invoice'),
    
    # Material Substitution (Vendor)
    path('vendor/substitutions/', views.vendor_substitutions, name='vendor_substitutions'),
    path('vendor/substitutions/create/', views.vendor_create_substitution, name='vendor_create_substitution'),
    
    # Jobs Management
    path('jobs/active/', views.active_jobs, name='active_jobs'),
    path('jobs/completed/', views.completed_jobs, name='completed_jobs'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    # path('jobs/<str:job_id>/accept/', views.accept_job, name='accept_job'),
    # path('jobs/<str:job_id>/decline/', views.decline_job, name='decline_job'),
    # path('jobs/<str:job_id>/submit-proof/', views.submit_proof, name='submit_proof'),
    # path('jobs/<str:job_id>/update-status/', views.update_job_status, name='update_job_status'),
    
    # QC Proofs
    path('vendor/proofs/', views.vendor_proofs, name='vendor_proofs'),
    
    # Invoices
    path('invoices/', views.invoices, name='invoices'),
    # path('invoices/create/', views.create_invoice, name='create_invoice'),
    # path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Performance
    path('performance/', views.performance, name='performance'),
    
    # Help & Support
    # path('help/', views.help_center, name='help'),
    # path('support/ticket/create/', views.create_support_ticket, name='create_ticket'),
    
    # API Endpoints for AJAX calls
    # path('api/jobs/search/', views.api_search_jobs, name='api_search_jobs'),
    # path('api/jobs/filter/', views.api_filter_jobs, name='api_filter_jobs'),
    # path('api/accept-all/', views.api_accept_all, name='api_accept_all'),
    # path('api/notifications/', views.api_get_notifications, name='api_notifications'),

    # Webhooks
    path('webhooks/mailgun/', views.mailgun_webhook, name='mailgun_webhook'),

]
