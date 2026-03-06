from rest_framework.routers import DefaultRouter
from django.urls import path

from . import api_views
from . import api_audit_logs
from . import api_analytics
from . import api_deliveries
from . import api_qc_inspections
from . import api_lpos
from . import api_payments
from . import storefront_views
from . import vendor_portal_views

router = DefaultRouter()

# Core CRM / AM
router.register("leads", api_views.LeadViewSet, basename="lead")
router.register("clients", api_views.ClientViewSet, basename="client")
router.register("client-contacts", api_views.ClientContactViewSet, basename="client-contact")
router.register("brand-assets", api_views.BrandAssetViewSet, basename="brand-asset")
router.register("compliance-documents", api_views.ComplianceDocumentViewSet, basename="compliance-document")

# Catalog / Products
router.register("products", api_views.ProductViewSet, basename="product")
router.register("storefront-products", api_views.StorefrontProductViewSet, basename="storefront-product")
router.register("product-approvals", api_views.ProductApprovalRequestViewSet, basename="product-approval")
router.register("property-types", api_views.PropertyTypeViewSet, basename="property-type")
router.register("property-values", api_views.PropertyValueViewSet, basename="property-value")
router.register("product-properties", api_views.ProductPropertyViewSet, basename="product-property")
router.register("quantity-pricing", api_views.QuantityPricingViewSet, basename="quantity-pricing")
router.register("turnaround-times", api_views.TurnAroundTimeViewSet, basename="turnaround-time")
router.register("product-images", api_views.ProductImageViewSet, basename="product-image")
router.register("product-videos", api_views.ProductVideoViewSet, basename="product-video")
router.register("product-downloads", api_views.ProductDownloadableFileViewSet, basename="product-download")
router.register("product-seo", api_views.ProductSEOViewSet, basename="product-seo")
router.register("product-review-settings", api_views.ProductReviewSettingsViewSet, basename="product-review-settings")
router.register("product-faqs", api_views.ProductFAQViewSet, basename="product-faq")
router.register("product-shipping", api_views.ProductShippingViewSet, basename="product-shipping")
router.register("product-legal", api_views.ProductLegalViewSet, basename="product-legal")
router.register("product-production", api_views.ProductProductionViewSet, basename="product-production")
router.register("product-change-history", api_views.ProductChangeHistoryViewSet, basename="product-change-history")
router.register("product-templates", api_views.ProductTemplateViewSet, basename="product-template")

# Costing & Process Configuration
router.register("processes", api_views.ProcessViewSet, basename="process")
router.register("process-tiers", api_views.ProcessTierViewSet, basename="process-tier")
router.register("process-variables", api_views.ProcessVariableViewSet, basename="process-variable")
router.register("product-variables", api_views.ProductVariableViewSet, basename="product-variable")
router.register("product-variable-options", api_views.ProductVariableOptionViewSet, basename="product-variable-option")
router.register("process-vendors", api_views.ProcessVendorViewSet, basename="process-vendor")
router.register("pricing-tiers", api_views.PricingTierViewSet, basename="pricing-tier")
router.register("vendor-tier-pricing", api_views.VendorTierPricingViewSet, basename="vendor-tier-pricing")
router.register("process-variable-ranges", api_views.ProcessVariableRangeViewSet, basename="process-variable-range")

# Quotes / Orders / Jobs
router.register("quotes", api_views.QuoteViewSet, basename="quote")
router.register("quote-line-items", api_views.QuoteLineItemViewSet, basename="quote-line-item")
router.register("jobs", api_views.JobViewSet, basename="job")
router.register("job-vendor-stages", api_views.JobVendorStageViewSet, basename="job-vendor-stage")
router.register("job-notes", api_views.JobNoteViewSet, basename="job-note")
router.register("job-attachments", api_views.JobAttachmentViewSet, basename="job-attachment")
router.register("timeline", api_views.TimelineEventViewSet, basename="timeline")
router.register("shipments", api_views.ShipmentViewSet, basename="shipment")



# Vendors / Purchasing / Finance
router.register("vendors", api_views.VendorViewSet, basename="vendor")
router.register("lpos", api_lpos.LPOViewSet, basename="lpo")
router.register("purchase-orders", api_views.PurchaseOrderViewSet, basename="purchase-order")
router.register("purchase-order-proofs", api_views.PurchaseOrderProofViewSet, basename="purchase-order-proof")
router.register("purchase-order-issues", api_views.PurchaseOrderIssueViewSet, basename="purchase-order-issue")
router.register("purchase-order-notes", api_views.PurchaseOrderNoteViewSet, basename="purchase-order-note")
router.register("material-substitutions", api_views.MaterialSubstitutionRequestViewSet, basename="material-substitution")
router.register("vendor-invoices", api_views.VendorInvoiceViewSet, basename="vendor-invoice")
router.register("payments", api_payments.PaymentViewSet, basename="payment")
router.register("vendor-quotes", api_views.VendorQuoteViewSet, basename="vendor-quote")
router.register("lpo-line-items", api_views.LPOLineItemViewSet, basename="lpo-line-item")
router.register("refunds", api_views.RefundViewSet, basename="refund")
router.register("credit-notes", api_views.CreditNoteViewSet, basename="credit-note")
router.register("adjustments", api_views.AdjustmentViewSet, basename="adjustment")



# Notifications / Logs / Settings / Integrations / QC / Delivery / Users / Dashboard
router.register("notifications", api_views.NotificationViewSet, basename="notification")
router.register("activity-log", api_views.ActivityLogViewSet, basename="activity-log")
router.register("system-settings", api_views.SystemSettingViewSet, basename="system-setting")
router.register("quickbooks", api_views.QuickBooksSyncViewSet, basename="quickbooks")
router.register("qc-inspections", api_qc_inspections.QCInspectionViewSet, basename="qc-inspection")
router.register("deliveries", api_deliveries.DeliveryViewSet, basename="delivery")
router.register("quote-attachments", api_views.QuoteAttachmentViewSet, basename="quote-attachment")
router.register("system-alerts", api_views.SystemAlertViewSet, basename="system-alert")
router.register("users", api_views.UserViewSet, basename="user")
router.register("groups", api_views.GroupViewSet, basename="group")
router.register("permissions", api_views.PermissionViewSet, basename="permission")
router.register("settings", api_views.SystemSettingViewSet, basename="settings")
router.register("audit-logs", api_audit_logs.AuditLogViewSet, basename="audit-logs")
router.register("dashboard", api_views.DashboardViewSet, basename="dashboard")
router.register("analytics", api_analytics.AnalyticsViewSet, basename="analytics")
router.register("search", api_views.SearchViewSet, basename="search")
router.register("product-rules", api_views.ProductRuleViewSet, basename="product-rule")
router.register("material-inventory", api_views.MaterialInventoryViewSet, basename="material-inventory")
router.register("webhook-subscriptions", api_views.WebhookSubscriptionViewSet, basename="webhook-subscription")
router.register("webhook-deliveries", api_views.WebhookDeliveryViewSet, basename="webhook-delivery")


# Production Team Specific APIs
router.register("production-updates", api_views.ProductionUpdateViewSet, basename="production-update")

# Task 8: Deadline Alerts
router.register("deadline-alerts", api_views.DeadlineAlertViewSet, basename="deadline-alert")

# Task 9: Job Files & Document Sharing
router.register("job-files", api_views.JobFileViewSet, basename="job-file")
router.register("document-shares", api_views.DocumentShareViewSet, basename="document-share")
router.register("costing-engine", api_views.CostingEngineViewSet, basename="costing-engine")
router.register("workload", api_views.WorkloadViewSet, basename="workload")
router.register("production-analytics", api_views.ProductionAnalyticsViewSet, basename="production-analytics")

# Production Team Portal - NEW APIs for vendor-PT integration
router.register("approval-thresholds", api_views.ApprovalThresholdViewSet, basename="approval-threshold")
router.register("invoice-disputes", api_views.InvoiceDisputeViewSet, basename="invoice-dispute")
router.register("job-progress-updates", api_views.JobProgressUpdateViewSet, basename="job-progress-update")
router.register("sla-escalations", api_views.SLAEscalationViewSet, basename="sla-escalation")
router.register("vendor-performance-metrics", api_views.VendorPerformanceMetricsViewSet, basename="vendor-performance-metrics")
router.register("profitability-analysis", api_views.ProfitabilityAnalysisViewSet, basename="profitability-analysis")

# Phase 2: Messaging, Progress, Proofs, and Performance APIs
router.register("messages", api_views.MessageViewSet, basename="message")
router.register("progress-updates", api_views.ProgressUpdateViewSet, basename="progress-update")
router.register("proof-submissions", api_views.ProofSubmissionViewSet, basename="proof-submission")

# Phase 3: Client Portal, Analytics, and Payment Tracking APIs
router.register("client-portal-notifications", api_views.ClientNotificationViewSet, basename="client-portal-notifications")
router.register("client-messages", api_views.ClientMessageViewSet, basename="client-message")
router.register("client-dashboard", api_views.ClientDashboardViewSet, basename="client-dashboard")
router.register("client-feedback", api_views.ClientFeedbackViewSet, basename="client-feedback")
router.register("order-metrics", api_views.OrderMetricsViewSet, basename="order-metrics")
router.register("vendor-comparison", api_views.VendorComparisonViewSet, basename="vendor-comparison")
router.register("performance-analytics", api_views.PerformanceAnalyticsViewSet, basename="performance-analytics")
router.register("payment-status", api_views.PaymentStatusViewSet, basename="payment-status")
router.register("payment-history", api_views.PaymentHistoryViewSet, basename="payment-history")

# Vendor Portal APIs
router.register("vendor-self-info", vendor_portal_views.VendorSelfInfoViewSet, basename="vendor-self-info")
router.register("vendor-portal-pos", vendor_portal_views.PurchaseOrderViewSet, basename="vendor-portal-po")
router.register("vendor-portal-invoices", vendor_portal_views.VendorInvoiceViewSet, basename="vendor-portal-invoice")
router.register("vendor-portal-proofs", vendor_portal_views.PurchaseOrderProofViewSet, basename="vendor-portal-proof")
router.register("vendor-performance", vendor_portal_views.VendorPerformanceViewSet, basename="vendor-performance")
router.register("vendor-portal-issues", vendor_portal_views.PurchaseOrderIssueViewSet, basename="vendor-portal-issue")
router.register("vendor-portal-notes", vendor_portal_views.PurchaseOrderNoteViewSet, basename="vendor-portal-note")
router.register("vendor-portal-substitutions", vendor_portal_views.MaterialSubstitutionRequestViewSet, basename="vendor-portal-substitution")
router.register("vendor-portal-performance", vendor_portal_views.VendorPerformanceViewSet, basename="vendor-portal-performance")

# Client Portal APIs
router.register("client-portal-users", api_views.ClientPortalUserViewSet, basename="client-portal-user")
router.register("client-orders", api_views.ClientOrderViewSet, basename="client-order")
router.register("client-invoices", api_views.ClientInvoiceViewSet, basename="client-invoice")
router.register("client-payments", api_views.ClientPaymentViewSet, basename="client-payment")
router.register("client-support-tickets", api_views.ClientSupportTicketViewSet, basename="client-support-ticket")
router.register("client-documents", api_views.ClientDocumentLibraryViewSet, basename="client-document")
router.register("client-notifications", api_views.ClientPortalNotificationViewSet, basename="client-notification")
router.register("client-activity-logs", api_views.ClientActivityLogViewSet, basename="client-activity-log")

# ============================================================================
# STOREFRONT ECOMMERCE APIs (v1)
# ============================================================================

# Estimate quotes
router.register("v1/storefront-estimates", storefront_views.EstimateQuoteViewSet, basename="storefront-estimate")

# Expose the main QuoteViewSet under the v1 prefix so AM and storefront flows
# can access quote actions at /api/v1/quotes/{id}/send-to-customer/ etc.
router.register("v1/quotes", api_views.QuoteViewSet, basename="v1-quote")

# Production units
router.register("v1/production-units", storefront_views.ProductionUnitViewSet, basename="production-unit")

# Chatbot conversations
router.register("v1/chatbot-conversations", storefront_views.ChatbotConversationViewSet, basename="chatbot-conversation")

# Storefront messages (for AM)
router.register("v1/storefront-messages", storefront_views.StorefrontMessageViewSet, basename="storefront-message")


urlpatterns = router.urls + [
    # Canonical Pricing Engine
    path('pricing/calculate/', api_views.PricingEngineView.as_view(), name='pricing-calculate'),
    # Product Configuration Rules Engine
    path('product-configurations/validate/', api_views.ProductConfigurationValidationView.as_view(), name='product-config-validate'),
    # Preflight Service
    path('files/preflight/', api_views.PreflightView.as_view(), name='preflight'),
    
    # ============================================================================
    # STOREFRONT ECOMMERCE ENDPOINTS (v1)
    # ============================================================================
    
    # Customer Authentication & Verification
    path('v1/customers/register/', storefront_views.CustomerRegistrationView.as_view(), name='storefront-register'),
    path('v1/customers/verify-email/', storefront_views.EmailVerificationView.as_view(), name='storefront-verify-email'),
    path('v1/customers/verify-phone/', storefront_views.PhoneVerificationView.as_view(), name='storefront-verify-phone'),
    path('v1/customers/login/', storefront_views.CustomerLoginView.as_view(), name='storefront-login'),
    path('v1/customers/profile/', storefront_views.CustomerProfileViewSet.as_view({'get': 'list', 'put': 'update'}), name='storefront-profile'),
    path('v1/customer/quotes/', storefront_views.CustomerQuotesListView.as_view(), name='customer-quotes'),
    
    # Contact & Messaging
    path('v1/contact/email/', storefront_views.ContactEmailView.as_view(), name='storefront-contact-email'),
    path('v1/contact/whatsapp/', storefront_views.ContactWhatsAppView.as_view(), name='storefront-contact-whatsapp'),
    path('v1/contact/call/', storefront_views.CallRequestView.as_view(), name='storefront-contact-call'),
    
    # Chatbot
    path('v1/chatbot/message/', storefront_views.ChatbotMessageView.as_view(), name='storefront-chatbot-message'),
    path('v1/chatbot/knowledge/', storefront_views.ChatbotKnowledgeView.as_view(), name='chatbot-knowledge'),
    
    # Quote Management
    path('v1/quotes/save-from-storefront/', storefront_views.SaveQuoteFromStorefrontView.as_view(), name='save-quote-from-storefront'),
]
