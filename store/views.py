from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg
from .models import Saree, Order, OrderItem, Coupon, Review, BrowsingHistory


# ===============================
# HOME PAGE
# ===============================
def home(request):
    query    = request.GET.get("q", "").strip()
    category = request.GET.get("category", "All")
    sort     = request.GET.get("sort", "")

    occasion = request.GET.get("occasion", "")

    sarees = Saree.objects.all()
    if query:
        from django.db.models import Q
        sarees = sarees.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(fabric__icontains=query) |
            Q(color__icontains=query) |
            Q(category__icontains=query) |
            Q(occasion__icontains=query)
        )
    if category and category != "All":
        sarees = sarees.filter(category__icontains=category)
    if occasion:
        sarees = sarees.filter(occasion__icontains=occasion)
    if sort == "price_asc":
        sarees = sarees.order_by("price")
    elif sort == "price_desc":
        sarees = sarees.order_by("-price")
    elif sort == "rating":
        sarees = sorted(sarees, key=lambda s: s.avg_rating(), reverse=True)
    else:
        sarees = sarees.order_by("-created_at")

    categories   = ["All", "Silk", "Cotton", "Bridal", "Party", "Designer"]
    wishlist     = request.session.get("wishlist", [])
    wishlist_ids = [str(i) for i in wishlist]

    return render(request, "store/home.html", {
        "sarees":       sarees,
        "categories":   categories,
        "wishlist_ids": wishlist_ids,
        "query":        query,
        "active_cat":   category,
        "active_sort":  sort,
        "active_occasion": occasion,
        "result_count": len(sarees) if isinstance(sarees, list) else sarees.count(),
    })


# ===============================
# PRODUCT DETAIL — track browsing history
# ===============================
def product_detail(request, saree_id):
    saree        = get_object_or_404(Saree, id=saree_id)
    wishlist     = request.session.get("wishlist", [])
    wishlist_ids = [str(i) for i in wishlist]
    in_cart      = str(saree_id) in request.session.get("cart", {})
    reviews      = saree.reviews.select_related("user").order_by("-created_at")
    user_review  = None

    # Track browsing history for logged-in users
    if request.user.is_authenticated:
        BrowsingHistory.objects.update_or_create(
            user=request.user, saree=saree,
            defaults={"saree": saree}
        )
        user_review = Review.objects.filter(saree=saree, user=request.user).first()

    # Related: based on browsing history (logged in) or same category (guest)
    if request.user.is_authenticated:
        history_ids = BrowsingHistory.objects.filter(
            user=request.user
        ).exclude(saree=saree).values_list("saree_id", flat=True)[:10]
        # Sarees from same categories as history, excluding current
        history_cats = Saree.objects.filter(id__in=history_ids).values_list("category", flat=True)
        related = Saree.objects.filter(
            category__in=history_cats
        ).exclude(id=saree_id).distinct()[:4]
        if not related:
            related = Saree.objects.filter(category=saree.category).exclude(id=saree_id)[:4]
    else:
        related = Saree.objects.filter(category=saree.category).exclude(id=saree_id)[:4]

    # Handle review submission
    if request.method == "POST" and request.user.is_authenticated:
        rating = int(request.POST.get("rating", 5))
        title  = request.POST.get("title", "")
        body   = request.POST.get("body", "")
        Review.objects.update_or_create(
            saree=saree, user=request.user,
            defaults={"rating": rating, "title": title, "body": body}
        )
        messages.success(request, "Your review has been submitted!")
        return redirect("product_detail", saree_id=saree_id)

    return render(request, "store/product_detail.html", {
        "saree":        saree,
        "related":      related,
        "wishlist_ids": wishlist_ids,
        "in_cart":      in_cart,
        "reviews":      reviews,
        "user_review":  user_review,
        "avg_rating":   saree.avg_rating(),
        "review_count": saree.review_count(),
    })


# ===============================
# AUTH — Register
# ===============================
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username  = request.POST.get("username", "").strip()
        email     = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            messages.success(request, f"Welcome to SareeStore, {username}! 🎉")
            return redirect("home")

    return render(request, "store/register.html")


# ===============================
# AUTH — Login
# ===============================
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user     = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Merge session orders into user account
            session_orders = request.session.get("my_orders", [])
            if session_orders:
                Order.objects.filter(id__in=session_orders, user__isnull=True).update(user=user)
                request.session["my_orders"] = []
            return redirect(request.GET.get("next", "home"))
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "store/login.html")


# ===============================
# AUTH — Logout
# ===============================
def logout_view(request):
    logout(request)
    return redirect("home")


# ===============================
# ADD TO CART
# ===============================
def add_to_cart(request, saree_id):
    cart = request.session.get("cart", {})
    cart[str(saree_id)] = cart.get(str(saree_id), 0) + 1
    request.session["cart"] = cart
    next_url = request.GET.get("next", "cart")
    if next_url == "detail":
        return redirect("product_detail", saree_id=saree_id)
    return redirect("cart")


# ===============================
# CART PAGE
# ===============================
def cart_view(request):
    cart        = request.session.get("cart", {})
    items       = []
    total_price = 0

    for saree_id, qty in cart.items():
        saree    = get_object_or_404(Saree, id=saree_id)
        subtotal = saree.price * qty
        total_price += subtotal
        items.append({"saree": saree, "qty": qty, "subtotal": subtotal})

    return render(request, "store/cart.html", {
        "items": items, "total_price": total_price,
    })


# ===============================
# CART ACTIONS
# ===============================
def remove_from_cart(request, saree_id):
    cart = request.session.get("cart", {})
    cart.pop(str(saree_id), None)
    request.session["cart"] = cart
    return redirect("cart")

def increase_qty(request, saree_id):
    cart = request.session.get("cart", {})
    if str(saree_id) in cart:
        cart[str(saree_id)] += 1
    request.session["cart"] = cart
    return redirect("cart")

def decrease_qty(request, saree_id):
    cart = request.session.get("cart", {})
    key  = str(saree_id)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0:
            del cart[key]
    request.session["cart"] = cart
    return redirect("cart")


# ===============================
# APPLY COUPON (AJAX-friendly POST)
# ===============================
def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip().upper()
        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_valid():
                request.session["coupon_code"] = code
                messages.success(request, f"Coupon '{code}' applied — {coupon.discount_pct}% off!")
            else:
                messages.error(request, "This coupon is expired or inactive.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    return redirect("checkout")

def remove_coupon(request):
    request.session.pop("coupon_code", None)
    return redirect("checkout")


# ===============================
# CHECKOUT
# ===============================
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart")

    items       = []
    subtotal    = 0

    for saree_id, qty in cart.items():
        saree    = get_object_or_404(Saree, id=saree_id)
        s        = saree.price * qty
        subtotal += s
        items.append({"saree": saree, "qty": qty, "subtotal": s})

    # Coupon
    coupon         = None
    discount       = 0
    coupon_code    = request.session.get("coupon_code", "")
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid():
                discount = round(subtotal * coupon.discount_pct / 100, 2)
        except Coupon.DoesNotExist:
            request.session.pop("coupon_code", None)

    total_price = subtotal - discount

    if request.method == "POST":
        order = Order.objects.create(
            user            = request.user if request.user.is_authenticated else None,
            customer_name   = request.POST.get("name"),
            phone           = request.POST.get("phone"),
            address         = request.POST.get("address"),
            city            = request.POST.get("city"),
            pincode         = request.POST.get("pincode"),
            total_amount    = total_price,
            discount_amount = discount,
            coupon          = coupon,
            is_paid         = False,
            status          = "pending",
        )
        for item in items:
            OrderItem.objects.create(order=order, saree=item["saree"], quantity=item["qty"])
            # Deduct stock
            saree = item["saree"]
            saree.stock = max(0, saree.stock - item["qty"])
            saree.save()

        if coupon:
            coupon.used_count += 1
            coupon.save()

        request.session["cart"] = {}
        request.session.pop("coupon_code", None)

        # Track in session for guests
        if not request.user.is_authenticated:
            order_ids = request.session.get("my_orders", [])
            order_ids.append(order.id)
            request.session["my_orders"] = order_ids

        # Send confirmation email
        _send_order_email(order, items, request.POST.get("email", ""))

        return redirect("success", order_id=order.id)

    return render(request, "store/checkout.html", {
        "items":       items,
        "subtotal":    subtotal,
        "discount":    discount,
        "total_price": total_price,
        "coupon":      coupon,
        "coupon_code": coupon_code,
    })


def _send_order_email(order, items, guest_email=""):
    """Send order confirmation email — silently fails if email not configured."""
    try:
        item_lines = "\n".join(
            f"  • {i['saree'].name} x{i['qty']} — ₹{i['subtotal']}" for i in items
        )
        body = f"""Hi {order.customer_name},

Thank you for your order at Tantira! 🎉

Order ID   : #{order.id}
Total      : ₹{order.total_amount}
{f"Discount   : ₹{order.discount_amount}" if order.discount_amount else ""}
Payment    : Cash on Delivery
Status     : Pending

Items ordered:
{item_lines}

Delivery to: {order.address}, {order.city} — {order.pincode}

Track your order at: http://127.0.0.1:8000/track-order/{order.id}/

Thank you for shopping with Tantira! 💛
"""
        # Get recipient email
        recipient = ""
        if order.user and order.user.email:
            recipient = order.user.email
        elif guest_email:
            recipient = guest_email

        if recipient:
            send_mail(
                subject    = f"Order Confirmed — Tantira #{order.id}",
                message    = body,
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [recipient],
                fail_silently  = True,
            )
    except Exception:
        pass   # Never crash the order flow because of email


# ===============================
# SUCCESS PAGE
# ===============================
def success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/success.html", {"order": order})


# ===============================
# MY ORDERS — login or session
# ===============================
def my_orders(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).prefetch_related("items__saree").order_by("-created_at")
    else:
        order_ids = request.session.get("my_orders", [])
        orders    = Order.objects.filter(id__in=order_ids).prefetch_related("items__saree").order_by("-created_at")
    return render(request, "store/my_orders.html", {"orders": orders})


# ===============================
# TRACK ORDER
# ===============================
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Security check
    if request.user.is_authenticated:
        if order.user != request.user:
            messages.error(request, "Order not found.")
            return redirect("my_orders")
    else:
        if order.id not in request.session.get("my_orders", []):
            messages.error(request, "Order not found.")
            return redirect("my_orders")

    steps = [
        {"key": "pending",    "label": "Order Placed", "icon": "📋"},
        {"key": "confirmed",  "label": "Confirmed",    "icon": "✅"},
        {"key": "processing", "label": "Processing",   "icon": "🏭"},
        {"key": "shipped",    "label": "Shipped",      "icon": "🚚"},
        {"key": "delivered",  "label": "Delivered",    "icon": "🎁"},
    ]
    current_step = order.step_index()
    progress_pct = 0 if current_step <= 0 else round(current_step / (len(steps) - 1) * 80)

    return render(request, "store/track_order.html", {
        "order": order, "steps": steps,
        "current_step": current_step, "progress_pct": progress_pct,
    })


# ===============================
# CANCEL ORDER
# ===============================
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.user.is_authenticated:
        if order.user != request.user:
            return redirect("my_orders")
    else:
        if order.id not in request.session.get("my_orders", []):
            return redirect("my_orders")

    if not order.can_cancel():
        messages.error(request, f"Cannot cancel — order is already {order.get_status_display()}.")
        return redirect("track_order", order_id=order.id)

    if request.method == "POST":
        order.status        = "cancelled"
        order.tracking_note = "Cancelled by customer."
        order.save()
        messages.success(request, f"Order #{order.id} cancelled.")
        return redirect("my_orders")

    return render(request, "store/cancel_confirm.html", {"order": order})


# ===============================
# WISHLIST
# ===============================
def add_to_wishlist(request, saree_id):
    wishlist = request.session.get("wishlist", [])
    if saree_id not in wishlist:
        wishlist.append(saree_id)
    request.session["wishlist"] = wishlist
    next_url = request.GET.get("next", "home")
    if next_url == "detail":
        return redirect("product_detail", saree_id=saree_id)
    return redirect("home")

def wishlist_view(request):
    wishlist = request.session.get("wishlist", [])
    sarees   = Saree.objects.filter(id__in=wishlist)
    return render(request, "store/wishlist.html", {"sarees": sarees})

def remove_from_wishlist(request, saree_id):
    wishlist = [i for i in request.session.get("wishlist", []) if str(i) != str(saree_id)]
    request.session["wishlist"] = wishlist
    return redirect("wishlist")


# ===============================
# PROFILE
# ===============================
def profile_view(request):
    if not request.user.is_authenticated:
        return redirect("/login/?next=/profile/")
    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_info":
            user.first_name = request.POST.get("first_name", "").strip()
            user.last_name  = request.POST.get("last_name", "").strip()
            email           = request.POST.get("email", "").strip()
            if email and email != user.email:
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    messages.error(request, "That email is already used by another account.")
                else:
                    user.email = email
            user.save()
            messages.success(request, "Profile updated successfully!")

        elif action == "change_password":
            old  = request.POST.get("old_password", "")
            new1 = request.POST.get("new_password1", "")
            new2 = request.POST.get("new_password2", "")
            if not user.check_password(old):
                messages.error(request, "Current password is incorrect.")
            elif new1 != new2:
                messages.error(request, "New passwords do not match.")
            elif len(new1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
            else:
                user.set_password(new1)
                user.save()
                login(request, user)
                messages.success(request, "Password changed successfully!")

        return redirect("profile")

    orders       = Order.objects.filter(user=user).prefetch_related("items")
    order_count  = orders.count()
    total_spent  = sum(o.total_amount for o in orders)
    recent_orders = orders.order_by("-created_at")[:5]
    wishlist_count = len(request.session.get("wishlist", []))

    return render(request, "store/profile.html", {
        "order_count":   order_count,
        "total_spent":   total_spent,
        "recent_orders": recent_orders,
        "wishlist_count": wishlist_count,
    })


# ===============================
# FORGOT PASSWORD
# ===============================
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        try:
            user = User.objects.get(email=email)
            # Generate token
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"http://127.0.0.1:8000/reset-password/{uid}/{token}/"
            # Send email
            send_mail(
                subject    = "Reset Your Tantira Password",
                message    = f"Hi {user.username},\n\nClick the link below to reset your password:\n{reset_url}\n\nThis link expires in 24 hours.\n\nTantira Team",
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [email],
                fail_silently  = True,
            )
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        messages.success(request, "If that email is registered, a reset link has been sent!")
        return redirect("forgot_password")
    return render(request, "store/forgot_password.html")


# ===============================
# RESET PASSWORD
# ===============================
def reset_password(request, uidb64, token):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    valid = False
    user  = None
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            valid = True
    except Exception:
        pass

    if request.method == "POST" and valid:
        new1 = request.POST.get("new_password1", "")
        new2 = request.POST.get("new_password2", "")
        if new1 != new2:
            messages.error(request, "Passwords do not match.")
        elif len(new1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            user.set_password(new1)
            user.save()
            messages.success(request, "Password reset! You can now log in.")
            return redirect("login")

    return render(request, "store/reset_password.html", {"valid": valid})


# ===============================
# ABOUT
# ===============================
def about_view(request):
    return render(request, "store/about.html")


# ===============================
# CONTACT
# ===============================
def contact_view(request):
    sent = False
    if request.method == "POST":
        name    = request.POST.get("name", "")
        email   = request.POST.get("email", "")
        subject = request.POST.get("subject", "")
        message = request.POST.get("message", "")
        try:
            send_mail(
                subject    = f"Tantira Contact: {subject} from {name}",
                message    = f"From: {name} <{email}>\n\n{message}",
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [settings.EMAIL_HOST_USER],
                fail_silently  = True,
            )
        except Exception:
            pass
        sent = True
    return render(request, "store/contact.html", {"sent": sent})


# ===============================
# FAQ
# ===============================
def faq_view(request):
    faqs_orders = [
        ("How long does delivery take?", "We deliver within 5–7 business days across India. Express delivery is available for select pin codes."),
        ("Can I track my order?", "Yes! Once your order is shipped, you can track it from My Orders → Track Order."),
        ("Can I cancel my order?", "You can cancel your order within 24 hours of placing it, as long as it hasn't been shipped."),
        ("Do you deliver outside India?", "Currently we deliver only within India. International shipping is coming soon!"),
    ]
    faqs_products = [
        ("Are your sarees authentic handwoven?", "Yes, every saree is sourced directly from certified weavers and artisan cooperatives across India."),
        ("How do I know my saree's fabric?", "Each product page clearly mentions the fabric, weave type, and care instructions."),
        ("Do you offer custom orders?", "Yes! Contact us for custom weave requests, blouse stitching, and bulk orders for events."),
    ]
    faqs_returns = [
        ("What is your return policy?", "We accept returns within 7 days of delivery for unused, unwashed items in original packaging."),
        ("How do I initiate a return?", "Contact us at support@tantira.com with your order ID and reason for return."),
        ("What payment methods do you accept?", "We currently accept Cash on Delivery. Online payment via Razorpay is coming soon."),
        ("Is COD available everywhere?", "COD is available for most pin codes across India. Enter your pincode at checkout to confirm."),
    ]
    return render(request, "store/faq.html", {
        "faqs_orders":   faqs_orders,
        "faqs_products": faqs_products,
        "faqs_returns":  faqs_returns,
    })


# ===============================
# ADMIN DASHBOARD
# ===============================
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")

    from django.db.models import Sum, Count
    from django.contrib.auth.models import User as AuthUser
    from django.utils import timezone
    import json, datetime

    orders = Order.objects.all()

    # ── Stats ──
    total_revenue   = orders.aggregate(t=Sum("total_amount"))["t"] or 0
    total_orders    = orders.count()
    pending_orders  = orders.filter(status="pending").count()
    delivered_orders = orders.filter(status="delivered").count()
    cancelled_orders = orders.filter(status="cancelled").count()
    total_customers = AuthUser.objects.filter(is_staff=False).count()
    total_products  = Saree.objects.count()
    low_stock       = Saree.objects.filter(stock__lte=3).count()
    recent_orders   = orders.prefetch_related("items__saree").order_by("-created_at")[:10]

    # ── Top products ──
    top_products = (
        OrderItem.objects
        .values("saree__name")
        .annotate(total=Sum("quantity"))
        .order_by("-total")[:6]
    )

    # ── Revenue last 7 days ──
    today = timezone.now().date()
    daily_labels = []
    daily_revenue = []
    daily_orders = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        rev = day_orders.aggregate(t=Sum("total_amount"))["t"] or 0
        daily_labels.append(day.strftime("%d %b"))
        daily_revenue.append(float(rev))
        daily_orders.append(day_orders.count())

    # ── Revenue last 6 months ──
    monthly_labels = []
    monthly_revenue = []
    for i in range(5, -1, -1):
        month = today.replace(day=1) - datetime.timedelta(days=i*30)
        month_orders = orders.filter(
            created_at__year=month.year,
            created_at__month=month.month
        )
        rev = month_orders.aggregate(t=Sum("total_amount"))["t"] or 0
        monthly_labels.append(month.strftime("%b %Y"))
        monthly_revenue.append(float(rev))

    # ── Category revenue ──
    cat_data = {}
    for item in OrderItem.objects.select_related("saree", "order"):
        cat = item.saree.category
        cat_data[cat] = cat_data.get(cat, 0) + float(item.saree.price * item.quantity)
    cat_labels = list(cat_data.keys())
    cat_values = [round(v, 2) for v in cat_data.values()]

    # ── Status chart ──
    status_map = {s[0]: s[1] for s in Order.STATUS_CHOICES}
    status_data = orders.values("status").annotate(count=Count("id"))
    status_labels = [status_map.get(s["status"], s["status"]) for s in status_data]
    status_counts  = [s["count"] for s in status_data]

    return render(request, "store/dashboard.html", {
        "total_revenue":    round(total_revenue, 2),
        "total_orders":     total_orders,
        "pending_orders":   pending_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_customers":  total_customers,
        "total_products":   total_products,
        "low_stock":        low_stock,
        "recent_orders":    recent_orders,
        "top_products":     top_products,
        "daily_labels":     json.dumps(daily_labels),
        "daily_revenue":    json.dumps(daily_revenue),
        "daily_orders":     json.dumps(daily_orders),
        "monthly_labels":   json.dumps(monthly_labels),
        "monthly_revenue":  json.dumps(monthly_revenue),
        "cat_labels":       json.dumps(cat_labels),
        "cat_values":       json.dumps(cat_values),
        "status_labels":    json.dumps(status_labels),
        "status_counts":    json.dumps(status_counts),
        "low_stock_items":   Saree.objects.filter(stock__lte=3).order_by("stock")[:8],
    })


# ===============================
# NEWSLETTER
# ===============================
def newsletter_signup(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if email:
            try:
                send_mail(
                    subject    = "New Newsletter Signup — Tantira",
                    message    = f"New subscriber: {email}",
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [settings.EMAIL_HOST_USER],
                    fail_silently  = True,
                )
                # Send welcome email to subscriber
                send_mail(
                    subject    = "Welcome to Tantira!",
                    message    = f"Thank you for subscribing to Tantira!\n\nYou'll be the first to know about new arrivals, exclusive offers and style inspiration.\n\nWith love,\nTantira Team",
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [email],
                    fail_silently  = True,
                )
            except Exception:
                pass
        messages.success(request, "Thank you for subscribing!")
    return redirect(request.META.get("HTTP_REFERER", "home"))

