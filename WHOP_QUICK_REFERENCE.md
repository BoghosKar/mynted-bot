# WHOP INTEGRATION - QUICK REFERENCE

## 🔑 Your Credentials
```
Company ID: biz_7iDflJsY9KDdBY
API Key: apik_w2L2JAbWdkh08_C4124204_C_0fcdcad7c9f48b972289ab554553ca4d7cdb49e74118450676974d40fa495d
Dashboard: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/
```

## ✅ What's Already Done

1. ✅ Webhook handler code written
2. ✅ Credit package mapping configured
3. ✅ `/buy` command updated with Whop link
4. ✅ Payment & refund processing implemented
5. ✅ Docker & start scripts updated
6. ✅ Memory bank documentation saved

## 📋 What You Need to Do Manually

### STEP 1: Create 4 Products in Whop
Go to: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/products

Create these products:
- **Mynted AI - Starter Pack** → $9.99 (one-time)
- **Mynted AI - Creator Pack** → $29.99 (one-time)
- **Mynted AI - Professional Pack** → $59.99 (one-time)
- **Mynted AI - Enterprise Pack** → $199.99 (one-time)

After creating, copy the product IDs (look like `prod_xxxxx`)

### STEP 2: Get Your Railway URL
```bash
railway domain
```

Or find it in: https://railway.com/project/5604b7a8-d850-49df-8813-ce34995c0f5f

### STEP 3: Create Webhook in Whop
Go to: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/developer

- URL: `https://<railway-url>/webhooks/whop`
- Events: `payment.succeeded`, `payment.failed`, `refund.created`
- Save the webhook secret

### STEP 4: Set Environment Variables
```bash
railway variables --set "WHOP_WEBHOOK_SECRET=<secret-from-step-3>"
railway variables --set "WHOP_STARTER_PRODUCT_ID=<product-id>"
railway variables --set "WHOP_CREATOR_PRODUCT_ID=<product-id>"
railway variables --set "WHOP_PROFESSIONAL_PRODUCT_ID=<product-id>"
railway variables --set "WHOP_ENTERPRISE_PRODUCT_ID=<product-id>"
```

### STEP 5: Deploy
```bash
railway up --detach
```

### STEP 6: Test
1. Make a test purchase on Whop
2. Check Railway logs: `railway logs`
3. Check credits in Discord: `/balance`

## 🔍 Troubleshooting Commands

```bash
# Check Railway logs
railway logs

# Check Railway status
railway status

# Check environment variables
railway variables

# Redeploy
railway up --detach
```

## 📞 Quick Links

- **Whop Dashboard**: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/
- **Railway Dashboard**: https://railway.com/project/5604b7a8-d850-49df-8813-ce34995c0f5f
- **Setup Guide**: See WHOP_SETUP_GUIDE.md for detailed instructions
- **Technical Docs**: See memory bank mynted-bot/whop-integration.md

---

**Status**: Webhook code ready ✅ | Manual setup required ⏳
