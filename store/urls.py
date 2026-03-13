from django.urls import path
from . import views

urlpatterns = [
    # ── Core ──
    path("",          views.home,     name="home"),
    path("cart/",     views.cart_view, name="cart"),
    path("checkout/", views.checkout,  name="checkout"),
    path("success/<int:order_id>/", views.success, name="success"),

    # ── Auth ──
    path("register/", views.register_view, name="register"),
    path("login/",    views.login_view,    name="login"),
    path("logout/",   views.logout_view,   name="logout"),
    path("profile/",        views.profile_view,  name="profile"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<uidb64>/<token>/", views.reset_password, name="reset_password"),

    # ── Pages ──
    path("about/",     views.about_view,    name="about"),
    path("contact/",   views.contact_view,  name="contact"),
    path("faq/",       views.faq_view,      name="faq"),
    path("dashboard/",  views.admin_dashboard,  name="dashboard"),
    path("newsletter/", views.newsletter_signup, name="newsletter"),

    # ── Product ──
    path("product/<int:saree_id>/", views.product_detail, name="product_detail"),

    # ── Cart actions ──
    path("add-to-cart/<int:saree_id>/",  views.add_to_cart,      name="add_to_cart"),
    path("remove/<int:saree_id>/",        views.remove_from_cart, name="remove_from_cart"),
    path("increase/<int:saree_id>/",      views.increase_qty,     name="increase_qty"),
    path("decrease/<int:saree_id>/",      views.decrease_qty,     name="decrease_qty"),

    # ── Coupon ──
    path("apply-coupon/",  views.apply_coupon,  name="apply_coupon"),
    path("remove-coupon/", views.remove_coupon, name="remove_coupon"),

    # ── Orders ──
    path("my-orders/",                   views.my_orders,    name="my_orders"),
    path("track-order/<int:order_id>/",  views.track_order,  name="track_order"),
    path("cancel-order/<int:order_id>/", views.cancel_order, name="cancel_order"),

    # ── Wishlist ──
    path("wishlist/",                       views.wishlist_view,        name="wishlist"),
    path("add-wishlist/<int:saree_id>/",    views.add_to_wishlist,      name="add_wishlist"),
    path("remove-wishlist/<int:saree_id>/", views.remove_from_wishlist, name="remove_wishlist"),
]
