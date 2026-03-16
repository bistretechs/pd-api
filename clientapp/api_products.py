import logging

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, SAFE_METHODS
from rest_framework.response import Response

from .models import (
    PrintCategory,
    Product,
    ProductCategory,
    ProductCompatibilityRule,
    ProductFamily,
    ProductSpecGroup,
    ProductSubCategory,
    ProductTag,
    SpecGroupLibrary,
    SpecGroupLibraryOption,
    SpecOption,
    SpecOptionRange,
    calculate_product_price,
)
from .permissions import IsAdmin, IsAccountManager, IsProductionTeam, IsCatalogEditor

logger = logging.getLogger(__name__)


# ── Serializers ───────────────────────────────────────────────────────────────


class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ["id", "name", "slug"]
        read_only_fields = ["slug"]


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "description"]
        read_only_fields = ["slug"]


class ProductSubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ["id", "category", "category_name", "name", "slug", "description"]
        read_only_fields = ["slug"]


class ProductFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFamily
        fields = ["id", "name", "slug", "description"]
        read_only_fields = ["slug"]


class PrintCategorySerializer(serializers.ModelSerializer):
    suggested_library_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=SpecGroupLibrary.objects.all(),
        required=False,
    )

    class Meta:
        model = PrintCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "default_bleed_mm",
            "default_safe_zone_mm",
            "default_min_dpi",
            "default_color_profile",
            "default_production_method",
            "suggested_library_groups",
        ]
        read_only_fields = ["slug"]


class SpecGroupLibraryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecGroupLibraryOption
        fields = [
            "id",
            "library_group",
            "name",
            "display_order",
            "is_default",
            "is_active",
            "quantity_value",
            "selling_price",
            "vendor_cost",
            "selling_price_modifier",
            "vendor_cost_modifier",
            "multiplier_value",
            "preview_image",
        ]


class SpecGroupLibrarySerializer(serializers.ModelSerializer):
    library_options = SpecGroupLibraryOptionSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = SpecGroupLibrary
        fields = [
            "id",
            "name",
            "description",
            "group_type",
            "display_label",
            "help_text",
            "is_required",
            "status",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "library_options",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SpecOptionRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecOptionRange
        fields = [
            "id",
            "spec_group",
            "range_from",
            "range_to",
            "unit_label",
            "selling_price_base",
            "selling_rate_per_unit",
            "vendor_cost_base",
            "vendor_rate_per_unit",
            "display_order",
        ]


class SpecOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecOption
        fields = [
            "id",
            "spec_group",
            "library_option",
            "name",
            "display_order",
            "is_default",
            "is_active",
            "quantity_value",
            "selling_price",
            "vendor_cost",
            "selling_price_modifier",
            "vendor_cost_modifier",
            "multiplier_value",
            "preview_image",
        ]


class ProductSpecGroupSerializer(serializers.ModelSerializer):
    options = SpecOptionSerializer(many=True, read_only=True)
    ranges = SpecOptionRangeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSpecGroup
        fields = [
            "id",
            "product",
            "library_group",
            "uses_library_options",
            "name",
            "display_label",
            "help_text",
            "group_type",
            "is_required",
            "display_order",
            "is_active",
            "parent_option",
            "dim_unit",
            "dim_width_min",
            "dim_width_max",
            "dim_height_min",
            "dim_height_max",
            "selling_rate_per_sqm",
            "vendor_rate_per_sqm",
            "min_selling_price",
            "min_vendor_cost",
            "header_image",
            "options",
            "ranges",
        ]


class ProductCompatibilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCompatibilityRule
        fields = [
            "id",
            "product",
            "rule_type",
            "condition_spec_group",
            "condition_option",
            "target_spec_group",
            "target_option",
            "error_message",
            "priority",
            "is_active",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    primary_category_name = serializers.CharField(
        source="primary_category.name", read_only=True
    )
    print_category_name = serializers.CharField(
        source="print_category.name", read_only=True
    )
    sub_category_name = serializers.CharField(
        source="sub_category.name", read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "internal_code",
            "short_description",
            "product_type",
            "pricing_mode",
            "status",
            "is_visible",
            "stock_status",
            "primary_category",
            "primary_category_name",
            "print_category",
            "print_category_name",
            "sub_category",
            "sub_category_name",
            "feature_product",
            "bestseller_badge",
            "new_arrival",
            "on_sale_badge",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProductDetailSerializer(serializers.ModelSerializer):
    tags = ProductTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProductTag.objects.all(),
        source="tags",
        write_only=True,
        required=False,
    )
    primary_category_name = serializers.CharField(
        source="primary_category.name", read_only=True
    )
    sub_category_name = serializers.CharField(
        source="sub_category.name", read_only=True
    )
    product_family_name = serializers.CharField(
        source="product_family.name", read_only=True
    )
    print_category_name = serializers.CharField(
        source="print_category.name", read_only=True
    )
    spec_groups = ProductSpecGroupSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "internal_code",
            "short_description",
            "long_description",
            "maintenance",
            "technical_specs",
            "print_category",
            "print_category_name",
            "primary_category",
            "primary_category_name",
            "sub_category",
            "sub_category_name",
            "product_family",
            "product_family_name",
            "product_type",
            "tags",
            "tag_ids",
            "pricing_mode",
            "status",
            "is_visible",
            "visibility",
            "feature_product",
            "bestseller_badge",
            "new_arrival",
            "new_arrival_expires",
            "on_sale_badge",
            "unit_of_measure",
            "unit_of_measure_custom",
            "weight",
            "weight_unit",
            "length",
            "width",
            "height",
            "dimension_unit",
            "warranty",
            "country_of_origin",
            "stock_status",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorders",
            "internal_notes",
            "client_notes",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
            "spec_groups",
        ]
        read_only_fields = ["internal_code", "created_at", "updated_at"]


class CatalogProductSerializer(serializers.ModelSerializer):
    tags = ProductTagSerializer(many=True, read_only=True)
    primary_category_name = serializers.CharField(
        source="primary_category.name", read_only=True
    )
    sub_category_name = serializers.CharField(
        source="sub_category.name", read_only=True
    )
    print_category_name = serializers.CharField(
        source="print_category.name", read_only=True
    )
    spec_groups = ProductSpecGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "internal_code",
            "short_description",
            "long_description",
            "maintenance",
            "technical_specs",
            "print_category",
            "print_category_name",
            "primary_category",
            "primary_category_name",
            "sub_category",
            "sub_category_name",
            "product_type",
            "tags",
            "pricing_mode",
            "is_visible",
            "visibility",
            "feature_product",
            "bestseller_badge",
            "new_arrival",
            "new_arrival_expires",
            "on_sale_badge",
            "unit_of_measure",
            "unit_of_measure_custom",
            "weight",
            "weight_unit",
            "length",
            "width",
            "height",
            "dimension_unit",
            "warranty",
            "country_of_origin",
            "stock_status",
            "spec_groups",
        ]


class PriceCalculationRequestSerializer(serializers.Serializer):
    selections = serializers.DictField(
        child=serializers.JSONField(),
        help_text=(
            "Map of spec_group_id (str) → value. "
            "Value may be: option_id (int), list of option_ids, "
            "numeric value, or {width, height} dict for dimension groups."
        ),
    )


# ── Viewsets ──────────────────────────────────────────────────────────────────


class _CatalogWriteMixin:
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsCatalogEditor()]


class ProductTagViewSet(_CatalogWriteMixin, viewsets.ModelViewSet):
    queryset = ProductTag.objects.all().order_by("name")
    serializer_class = ProductTagSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class ProductCategoryViewSet(_CatalogWriteMixin, viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all().order_by("name")
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class ProductSubCategoryViewSet(_CatalogWriteMixin, viewsets.ModelViewSet):
    queryset = (
        ProductSubCategory.objects.select_related("category").all().order_by("name")
    )
    serializer_class = ProductSubCategorySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        return qs


class ProductFamilyViewSet(_CatalogWriteMixin, viewsets.ModelViewSet):
    queryset = ProductFamily.objects.all().order_by("name")
    serializer_class = ProductFamilySerializer


class PrintCategoryViewSet(_CatalogWriteMixin, viewsets.ModelViewSet):
    queryset = PrintCategory.objects.prefetch_related("suggested_library_groups").all().order_by("name")
    serializer_class = PrintCategorySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class SpecGroupLibraryViewSet(viewsets.ModelViewSet):
    queryset = (
        SpecGroupLibrary.objects.prefetch_related("library_options")
        .select_related("created_by")
        .all()
        .order_by("name")
    )
    serializer_class = SpecGroupLibrarySerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        group_type = self.request.query_params.get("group_type")
        status_param = self.request.query_params.get("status")
        name = self.request.query_params.get("name")
        if group_type:
            qs = qs.filter(group_type=group_type)
        if status_param:
            qs = qs.filter(status=status_param)
        if name:
            qs = qs.filter(name__icontains=name)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"], url_path="options")
    def options(self, request, pk=None):
        library_group = self.get_object()
        library_options = library_group.library_options.all().order_by("display_order")
        serializer = SpecGroupLibraryOptionSerializer(library_options, many=True)
        return Response(serializer.data)


class SpecGroupLibraryOptionViewSet(viewsets.ModelViewSet):
    queryset = SpecGroupLibraryOption.objects.all().order_by("display_order")
    serializer_class = SpecGroupLibraryOptionSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        library_group = self.request.query_params.get("library_group")
        if library_group:
            qs = qs.filter(library_group_id=library_group)
        return qs


class ProductSpecGroupViewSet(viewsets.ModelViewSet):
    queryset = (
        ProductSpecGroup.objects.prefetch_related("options", "ranges")
        .select_related("product", "library_group")
        .all()
        .order_by("product", "display_order")
    )
    serializer_class = ProductSpecGroupSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get("product")
        is_active = self.request.query_params.get("is_active")
        if product:
            qs = qs.filter(product_id=product)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response(
                {"detail": "Expected a list of {id, display_order} objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated_count = 0
        for item in items:
            spec_group_id = item.get("id")
            display_order = item.get("display_order")
            if spec_group_id is None or display_order is None:
                return Response(
                    {"detail": "Each item must contain 'id' and 'display_order'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ProductSpecGroup.objects.filter(pk=spec_group_id).update(
                display_order=display_order
            )
            updated_count += 1
        return Response({"updated": updated_count})


class SpecOptionViewSet(viewsets.ModelViewSet):
    queryset = SpecOption.objects.all().order_by("spec_group", "display_order")
    serializer_class = SpecOptionSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        spec_group = self.request.query_params.get("spec_group")
        is_active = self.request.query_params.get("is_active")
        if spec_group:
            qs = qs.filter(spec_group_id=spec_group)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs


class SpecOptionRangeViewSet(viewsets.ModelViewSet):
    queryset = SpecOptionRange.objects.all().order_by("spec_group", "display_order")
    serializer_class = SpecOptionRangeSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        spec_group = self.request.query_params.get("spec_group")
        if spec_group:
            qs = qs.filter(spec_group_id=spec_group)
        return qs


class ProductCompatibilityRuleViewSet(viewsets.ModelViewSet):
    queryset = ProductCompatibilityRule.objects.all().order_by("product", "priority")
    serializer_class = ProductCompatibilityRuleSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get("product")
        rule_type = self.request.query_params.get("rule_type")
        is_active = self.request.query_params.get("is_active")
        if product:
            qs = qs.filter(product_id=product)
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs


class ProductAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam | IsAccountManager]

    def get_queryset(self):
        qs = (
            Product.objects.select_related(
                "print_category",
                "primary_category",
                "sub_category",
                "product_family",
                "created_by",
                "updated_by",
            )
            .prefetch_related("tags", "spec_groups__options", "spec_groups__ranges")
            .order_by("-created_at")
        )
        status_param = self.request.query_params.get("status")
        pricing_mode = self.request.query_params.get("pricing_mode")
        product_type = self.request.query_params.get("product_type")
        category = self.request.query_params.get("category")
        print_category = self.request.query_params.get("print_category")
        search = self.request.query_params.get("search")
        if status_param:
            qs = qs.filter(status=status_param)
        if pricing_mode:
            qs = qs.filter(pricing_mode=pricing_mode)
        if product_type:
            qs = qs.filter(product_type=product_type)
        if category:
            qs = qs.filter(primary_category_id=category)
        if print_category:
            qs = qs.filter(print_category_id=print_category)
        if search:
            qs = qs.filter(
                name__icontains=search
            ) | qs.filter(
                internal_code__icontains=search
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        product = self.get_object()
        can_publish, error_msg = product.can_be_published()
        if not can_publish:
            return Response(
                {"detail": error_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.status = "published"
        product.save(update_fields=["status"])
        return Response({"status": "published"})

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        product = self.get_object()
        product.status = "archived"
        product.save(update_fields=["status"])
        return Response({"status": "archived"})


class ProductCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CatalogProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            Product.objects.filter(status="published", is_visible=True)
            .select_related("print_category", "primary_category", "sub_category")
            .prefetch_related(
                "tags",
                "spec_groups__options",
                "spec_groups__ranges",
            )
            .order_by("-feature_product", "name")
        )
        category = self.request.query_params.get("category")
        print_category = self.request.query_params.get("print_category")
        pricing_mode = self.request.query_params.get("pricing_mode")
        search = self.request.query_params.get("search")
        tag = self.request.query_params.get("tag")
        if category:
            qs = qs.filter(primary_category_id=category)
        if print_category:
            qs = qs.filter(print_category_id=print_category)
        if pricing_mode:
            qs = qs.filter(pricing_mode=pricing_mode)
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(
                short_description__icontains=search
            )
        if tag:
            qs = qs.filter(tags__slug=tag)
        return qs.distinct()

    @action(detail=True, methods=["post"], url_path="calculate-price")
    def calculate_price(self, request, pk=None):
        product = self.get_object()
        if product.pricing_mode != "auto_calculate":
            return Response(
                {"detail": "This product requires a manual quote. Please contact us."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request_serializer = PriceCalculationRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        raw_selections: dict = request_serializer.validated_data["selections"]
        int_keyed_selections = {}
        for key, value in raw_selections.items():
            try:
                int_keyed_selections[int(key)] = value
            except (ValueError, TypeError):
                return Response(
                    {"detail": f"Invalid spec_group_id key: '{key}'. Keys must be integers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        result = calculate_product_price(product, int_keyed_selections)
        if result.errors:
            return Response(
                {
                    "valid": False,
                    "errors": result.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(
            {
                "valid": True,
                "final_selling_price": str(result.final_selling_price),
                "final_vendor_cost": str(result.final_vendor_cost),
                "margin_percent": str(result.margin_percent),
                "line_items": result.line_items,
            }
        )
