# TLS Bootstrap Problem (Chicken-Egg Problem)

---

## The Problem in Simple Terms

When setting up HTTPS for a new website, we face a circular dependency:

1. **To get an HTTPS certificate**, a certificate authority (Let's Encrypt) needs to verify we own the domain by making an HTTP request to our site
2. **But our site redirects all HTTP to HTTPS** (for security)
3. **The redirect fails** because we don't have a certificate yet

This is the "chicken-egg" problem: we need HTTPS to get a certificate, but we need a certificate to have HTTPS.

---

## How It Works (Technical Details)

### Normal HTTPS Flow

```
User → HTTP request → Server redirects to HTTPS → User connects via HTTPS
```

### Certificate Issuance Flow (HTTP-01 Challenge)

```
1. We request a certificate from Let's Encrypt
2. Let's Encrypt generates a secret token
3. Let's Encrypt makes an HTTP request to: http://our-domain/.well-known/acme-challenge/<token>
4. Our server must respond with the correct token (proves we control the domain)
5. Let's Encrypt issues the certificate
```

### Where It Breaks (with F5 NGINX)

With F5 NGINX Ingress Controller, the problem is different. F5 NGINX does not allow multiple Ingress resources for the same hostname:

```
Main Ingress deployed first (claims host)
     ↓
Certificate created → Solver Ingress created → REJECTED (host already taken)
```

---

## Our Infrastructure Context

We use:
- **F5 NGINX Ingress Controller** - routes traffic to our services
- **cert-manager** - automates certificate issuance
- **Let's Encrypt** - free certificate authority

### F5 NGINX Specific Limitation

The F5 NGINX Ingress Controller does not allow multiple Ingress resources for the same hostname. When cert-manager creates a temporary Ingress for the ACME challenge, it conflicts with our main Ingress.

```
Main Ingress: test.eshop-test.com → api-gateway (CLAIMED)
Solver Ingress: test.eshop-test.com → acme-solver (REJECTED - host taken)
```

---

## Solution: Certificate First

We create the Certificate resource before deploying the main Ingress. This way, the solver Ingress is the only one for the host, avoiding the conflict:

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
Step 1              │  Create Certificate resource                │
                    │  (no main ingress exists yet)               │
                    │                                             │
                    └─────────────────┬───────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │                                             │
Step 2              │  cert-manager creates solver Ingress        │
                    │  (only ingress for this host - no conflict) │
                    │                                             │
                    └─────────────────┬───────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │                                             │
Step 3              │  Let's Encrypt verifies via HTTP            │
                    │  Certificate issued → Secret created        │
                    │                                             │
                    └─────────────────┬───────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │                                             │
Step 4              │  Deploy main Ingress with TLS               │
                    │  (uses existing Secret)                     │
                    │                                             │
                    └─────────────────────────────────────────────┘
```

The main Ingress does not have `cert-manager.io/cluster-issuer` annotation. It only references the Secret that was already created by the Certificate resource.

---

## When This Happens

This bootstrap process is only needed:
- When setting up a **new environment** for the first time
- When the certificate **expires and the secret is deleted**
- When changing to a **new domain name**

Once the certificate exists, cert-manager automatically renews it before expiration (no manual steps needed).

---

## Related Documentation

- [Environment Setup](setup-env.md) - Full setup instructions including TLS bootstrap steps
