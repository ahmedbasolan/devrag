# E-Commerce API Documentation

## Overview

This is a RESTful API for managing an online store. It handles user authentication, product management, order processing, and payment integration.

## Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

### Register

```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepass123",
  "role": "customer"
}
```

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "securepass123"
}
```

Returns a JWT token valid for 24 hours.

## Products

### List Products

```http
GET /api/products?category=electronics
```

Returns all active products. Filter by category using query parameter.

### Get Product

```http
GET /api/products/42
```

### Create Product (Vendor only)

```http
POST /api/products
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless mouse with USB receiver",
  "price": 29.99,
  "stock": 150,
  "category": "electronics",
  "vendor_id": 5
}
```

## Orders

### Create Order

```http
POST /api/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 42,
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 5, "quantity": 1}
  ]
}
```

### Update Order Status

```http
PUT /api/orders/123/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "shipped"
}
```

Valid transitions:
- `pending` → `paid`, `cancelled`
- `paid` → `shipped`, `cancelled`
- `shipped` → `delivered`
- `delivered` → (none)
- `cancelled` → (none)

## Search

```http
GET /api/search?q=wireless+mouse
```

Full-text search across product names, descriptions, and categories.

## Admin

### Dashboard Stats

```http
GET /api/admin/stats
Authorization: Bearer <token>
```

Returns:
- Total users
- Total products
- Total orders
- Pending orders
- Total revenue

## Rate Limiting

API endpoints are rate-limited to 100 requests per minute per IP address. Exceeding this limit returns a 429 status code.

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request - invalid data |
| 401 | Unauthorized - invalid or missing token |
| 403 | Forbidden - insufficient permissions |
| 404 | Not found |
| 409 | Conflict - duplicate resource |
| 429 | Too many requests - rate limit exceeded |
