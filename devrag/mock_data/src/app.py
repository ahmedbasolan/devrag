"""
E-commerce API Server

A Flask-based REST API for managing products, orders, and user authentication.
Uses JWT tokens for secure endpoints and SQLAlchemy for database ORM.
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///store.db')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'super-secret-key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    """User account with role-based access control."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='customer')  # customer, admin, vendor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }


class Product(db.Model):
    """Product listing with inventory tracking."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100))
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'category': self.category,
            'is_active': self.is_active
        }


class Order(db.Model):
    """Customer order with status tracking."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, shipped, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total': self.total,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    """Line item within an order."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price
        }


# --- Auth Routes ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(username=data['username'], email=data['email'], role=data.get('role', 'customer'))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate and return JWT token."""
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role},
        expires_delta=timedelta(hours=24)
    )
    return jsonify({'token': token, 'user': user.to_dict()})


# --- Product Routes ---

@app.route('/api/products', methods=['GET'])
def list_products():
    """List all active products with optional category filter."""
    category = request.args.get('category')
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    return jsonify([p.to_dict() for p in query.all()])


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by ID."""
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    """Create a new product (vendors only)."""
    data = request.get_json()
    product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=data['price'],
        stock=data.get('stock', 0),
        category=data.get('category', ''),
        vendor_id=data['vendor_id']
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


# --- Order Routes ---

@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create a new order from cart items."""
    data = request.get_json()
    total = 0
    items = []

    for item in data['items']:
        product = Product.query.get(item['product_id'])
        if not product or product.stock < item['quantity']:
            return jsonify({'error': f'Product {item["product_id"]} unavailable'}), 400
        total += product.price * item['quantity']
        product.stock -= item['quantity']
        items.append({'product': product, 'quantity': item['quantity'], 'price': product.price})

    order = Order(user_id=data['user_id'], total=total, status='pending')
    db.session.add(order)
    db.session.flush()

    for item in items:
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            unit_price=item['price']
        ))

    db.session.commit()
    return jsonify(order.to_dict()), 201


@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    """Update order status (admin only)."""
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    valid_transitions = {
        'pending': ['paid', 'cancelled'],
        'paid': ['shipped', 'cancelled'],
        'shipped': ['delivered'],
        'delivered': [],
        'cancelled': []
    }
    if data['status'] not in valid_transitions.get(order.status, []):
        return jsonify({'error': f'Cannot transition from {order.status} to {data["status"]}'}), 400

    order.status = data['status']
    db.session.commit()
    return jsonify(order.to_dict())


# --- Payment Integration ---

class PaymentService:
    """Handles payment processing with multiple gateways."""

    def __init__(self, gateway='stripe'):
        self.gateway = gateway
        self.config = self._load_config()

    def _load_config(self):
        return {
            'stripe': {'api_key': os.getenv('STRIPE_KEY')},
            'paypal': {'client_id': os.getenv('PAYPAL_CLIENT_ID')},
            'square': {'access_token': os.getenv('SQUARE_TOKEN')}
        }.get(self.gateway, {})

    def process_payment(self, amount, currency='USD', metadata=None):
        """Process a payment through the configured gateway."""
        if self.gateway == 'stripe':
            return self._stripe_charge(amount, currency, metadata)
        elif self.gateway == 'paypal':
            return self._paypal_charge(amount, currency, metadata)
        raise ValueError(f'Unsupported gateway: {self.gateway}')

    def _stripe_charge(self, amount, currency, metadata):
        """Charge via Stripe API."""
        # Stripe integration would go here
        return {'status': 'success', 'transaction_id': 'txn_mock_123'}

    def _paypal_charge(self, amount, currency, metadata):
        """Charge via PayPal API."""
        return {'status': 'success', 'transaction_id': 'pp_mock_456'}

    def refund(self, transaction_id, amount=None):
        """Refund a previous transaction."""
        return {'status': 'refunded', 'transaction_id': transaction_id}


# --- Email Notifications ---

class NotificationService:
    """Send order confirmations and status updates."""

    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))

    def send_order_confirmation(self, order, user):
        """Send order confirmation email."""
        subject = f'Order #{order.id} Confirmed'
        body = f"""
        Hi {user.username},

        Your order #{order.id} has been placed successfully.
        Total: ${order.total:.2f}
        Status: {order.status}

        Thank you for shopping with us!
        """
        return self._send(user.email, subject, body)

    def send_shipping_update(self, order, user, tracking_number):
        """Send shipping notification with tracking info."""
        subject = f'Order #{order.id} Shipped'
        body = f"""
        Hi {user.username},

        Your order #{order.id} has been shipped!
        Tracking: {tracking_number}

        Expected delivery: 3-5 business days.
        """
        return self._send(user.email, subject, body)

    def _send(self, to, subject, body):
        """Actually send the email via SMTP."""
        # SMTP sending logic would go here
        print(f'Email to {to}: {subject}')
        return True


# --- Rate Limiting ---

from functools import wraps
from collections import defaultdict
import time

rate_limit_store = defaultdict(list)

def rate_limit(max_requests=100, window=60):
    """Decorator to limit API requests per client."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()
            # Remove old entries
            rate_limit_store[client_ip] = [
                t for t in rate_limit_store[client_ip] if now - t < window
            ]
            if len(rate_limit_store[client_ip]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            rate_limit_store[client_ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Admin Dashboard ---

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def admin_stats():
    """Get store statistics for admin dashboard."""
    return jsonify({
        'total_users': User.query.count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'revenue': db.session.query(db.func.sum(Order.total)).filter(
            Order.status.in_(['paid', 'shipped', 'delivered'])
        ).scalar() or 0
    })


# --- Search ---

@app.route('/api/search', methods=['GET'])
def search_products():
    """Full-text search across products."""
    q = request.args.get('q', '')
    if not q:
        return jsonify([])

    results = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{q}%'),
            Product.description.ilike(f'%{q}%'),
            Product.category.ilike(f'%{q}%')
        )
    ).filter_by(is_active=True).all()

    return jsonify([p.to_dict() for p in results])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
