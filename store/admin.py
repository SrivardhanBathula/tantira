from django.contrib import admin
from django.utils.html import format_html
from .models import Saree, Order, OrderItem, Coupon, Review, BrowsingHistory, Fabric


class OrderItemInline(admin.TabularInline):
    model           = OrderItem
    extra           = 0
    readonly_fields = ("saree", "quantity", "item_subtotal")
    def item_subtotal(self, obj): return f"₹{obj.subtotal()}"
    item_subtotal.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ("id", "customer_name", "phone", "city", "total_amount", "discount_amount", "status_badge", "is_paid", "created_at")
    list_filter   = ("status", "is_paid", "city")
    search_fields = ("customer_name", "phone", "city", "id")
    ordering      = ("-created_at",)
    inlines       = [OrderItemInline]
    readonly_fields = ("total_amount", "discount_amount", "coupon")
    fieldsets = (
        ("Customer Info",    {"fields": ("user", "customer_name", "phone", "address", "city", "pincode")}),
        ("Order Details",    {"fields": ("total_amount", "discount_amount", "coupon", "is_paid")}),
        ("Status & Tracking",{"fields": ("status", "tracking_note")}),
    )

    def status_badge(self, obj):
        colours = {"pending":"#856404","confirmed":"#0C5460","processing":"#155724","shipped":"#004085","delivered":"#155724","cancelled":"#721C24"}
        bgs     = {"pending":"#FFF3CD","confirmed":"#D1ECF1","processing":"#D4EDDA","shipped":"#CCE5FF","delivered":"#D4EDDA","cancelled":"#F8D7DA"}
        return format_html('<span style="padding:3px 10px;border-radius:12px;background:{};color:{};font-size:11px;font-weight:600;">{}</span>', bgs.get(obj.status,"#eee"), colours.get(obj.status,"#333"), obj.get_status_display())
    status_badge.short_description = "Status"

    actions = ["mark_confirmed", "mark_shipped", "mark_delivered"]
    def mark_confirmed(self, request, qs):
        n = qs.filter(status="pending").update(status="confirmed")
        self.message_user(request, f"{n} order(s) confirmed.")
    mark_confirmed.short_description = "✅ Mark as Confirmed"
    def mark_shipped(self, request, qs):
        n = qs.exclude(status__in=["delivered","cancelled"]).update(status="shipped")
        self.message_user(request, f"{n} order(s) shipped.")
    mark_shipped.short_description = "🚚 Mark as Shipped"
    def mark_delivered(self, request, qs):
        n = qs.filter(status="shipped").update(status="delivered")
        self.message_user(request, f"{n} order(s) delivered.")
    mark_delivered.short_description = "🎁 Mark as Delivered"


@admin.register(Fabric)
class FabricAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)
    ordering      = ("name",)


@admin.register(Saree)
class SareeAdmin(admin.ModelAdmin):
    list_display  = ("name", "category", "occasion", "fabric", "price", "stock")
    list_filter   = ("category", "occasion", "fabric")
    search_fields = ("name", "color", "description", "fabric")
    ordering      = ("-created_at",)
    fieldsets = (
        ("Basic Info", {"fields": ("name", "price", "category", "occasion")}),
        ("Details",    {"fields": ("fabric", "color", "stock", "description")}),
        ("Images",     {"fields": ("image", "hover_image", "image3", "image4")}),
    )


admin.site.register(OrderItem)
admin.site.register(BrowsingHistory)


# ===============================
# COUPON ADMIN
# ===============================
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ("code", "discount_pct", "is_active", "valid_from", "valid_to", "used_count", "max_uses")
    list_filter   = ("is_active",)
    search_fields = ("code",)
    ordering      = ("-valid_from",)


# ===============================
# REVIEW ADMIN
# ===============================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ("saree", "user", "rating", "title", "created_at")
    list_filter   = ("rating",)
    search_fields = ("saree__name", "user__username", "title")
    ordering      = ("-created_at",)
 


