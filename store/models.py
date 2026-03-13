from django.db import models
from django.contrib.auth.models import User


# ===============================
# FABRIC MODEL
# ===============================
class Fabric(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


# ===============================
# SAREE MODEL
# ===============================
class Saree(models.Model):

    CATEGORY_CHOICES = [
        ("Saree",   "Saree"),
        ("Lehenga", "Lehenga"),
        ("Salwar",  "Salwar Kameez"),
        ("Kurti",   "Kurti"),
        ("Anarkali","Anarkali"),
    ]

    OCCASION_CHOICES = [
        ("",           "— No Occasion —"),
        ("Wedding",    "Wedding"),
        ("Engagement", "Engagement"),
        ("Mehendi",    "Mehendi"),
        ("Reception",  "Reception"),
        ("Festival",   "Festival"),
        ("Party",      "Party"),
        ("Casual",     "Casual"),
        ("Office",     "Office"),
    ]

    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    fabric      = models.CharField(max_length=100, blank=True, default="")
    color       = models.CharField(max_length=100)
    stock       = models.IntegerField(default=1)
    category    = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Saree")
    occasion    = models.CharField(max_length=50, choices=OCCASION_CHOICES, blank=True, default="")
    image       = models.ImageField(upload_to="sarees/", blank=True, null=True)
    hover_image = models.ImageField(upload_to="sarees/", blank=True, null=True)
    image3      = models.ImageField(upload_to="sarees/", blank=True, null=True)
    image4      = models.ImageField(upload_to="sarees/", blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def avg_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def review_count(self):
        return self.reviews.count()


# ===============================
# COUPON MODEL
# ===============================
class Coupon(models.Model):
    code         = models.CharField(max_length=20, unique=True)
    discount_pct = models.IntegerField(help_text="Discount percentage e.g. 10 for 10%")
    is_active    = models.BooleanField(default=True)
    valid_from   = models.DateTimeField()
    valid_to     = models.DateTimeField()
    max_uses     = models.IntegerField(default=100)
    used_count   = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.code} — {self.discount_pct}% off"

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            self.used_count < self.max_uses
        )


# ===============================
# ORDER MODEL
# ===============================
class Order(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"), ("confirmed", "Confirmed"),
        ("processing", "Processing"), ("shipped", "Shipped"),
        ("delivered", "Delivered"), ("cancelled", "Cancelled"),
    ]
    STATUS_STEPS = ["pending", "confirmed", "processing", "shipped", "delivered"]

    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name = models.CharField(max_length=200)
    phone         = models.CharField(max_length=20)
    address       = models.TextField()
    city          = models.CharField(max_length=100)
    pincode       = models.CharField(max_length=10)
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon        = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    is_paid       = models.BooleanField(default=False)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    tracking_note = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

    def can_cancel(self):
        return self.status in ("pending", "confirmed")

    def step_index(self):
        if self.status == "cancelled":
            return -1
        try:
            return self.STATUS_STEPS.index(self.status)
        except ValueError:
            return 0


# ===============================
# ORDER ITEM MODEL
# ===============================
class OrderItem(models.Model):
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    saree    = models.ForeignKey(Saree, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.saree.name} x {self.quantity}"

    def subtotal(self):
        return self.saree.price * self.quantity


# ===============================
# REVIEW MODEL
# ===============================
class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    saree      = models.ForeignKey(Saree, on_delete=models.CASCADE, related_name="reviews")
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    rating     = models.IntegerField(choices=RATING_CHOICES)
    title      = models.CharField(max_length=100, blank=True)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("saree", "user")   # one review per user per saree

    def __str__(self):
        return f"{self.user.username} — {self.saree.name} ({self.rating}★)"


# ===============================
# BROWSING HISTORY MODEL
# ===============================
class BrowsingHistory(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="history")
    saree     = models.ForeignKey(Saree, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "saree")
        ordering        = ["-viewed_at"]
        verbose_name        = "Browsing History"
        verbose_name_plural = "Browsing Histories"

    def __str__(self):
        return f"{self.user.username} viewed {self.saree.name}"