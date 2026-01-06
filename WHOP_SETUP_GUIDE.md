# WHOP SETUP GUIDE - MYNTED AI

## Your Whop Information
- **Company ID**: `biz_7iDflJsY9KDdBY`
- **API Key**: `apik_w2L2JAbWdkh08_C4124204_C_0fcdcad7c9f48b972289ab554553ca4d7cdb49e74118450676974d40fa495d`
- **Dashboard**: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/

---

## STEP 1: CREATE YOUR PRODUCT

### Navigate to Products
1. Go to https://whop.com/dashboard/biz_7iDflJsY9KDdBY/
2. Click **Products** in the left sidebar
3. Click **Add product** button (top right)

### Configure Product Details
**Title**: `Mynted AI Credits`

**Description**:
```
Generate stunning AI images directly in Discord with Mynted AI.

Our advanced multi-layer AI pipeline combines Claude (for context understanding and prompt optimization) with Gemini (for image generation) to create high-quality images from your text descriptions.

Perfect for:
- Content creators
- Digital artists
- Marketing teams
- Social media managers
```

**Pricing Model**: One-time payment (we'll add 4 different packages)

---

## STEP 2: CREATE PRICING PLANS

You need to create **4 separate products** (one for each credit package):

### Package 1: Starter Pack
- **Product Name**: `Mynted AI - Starter Pack`
- **Pricing Type**: One-time payment
- **Price**: `$9.99`
- **Currency**: USD
- **Description**: `50 credits - Perfect for trying out Mynted AI`
- **Stock Limit**: Unlimited
- **Visibility**: Visible

### Package 2: Creator Pack
- **Product Name**: `Mynted AI - Creator Pack`
- **Pricing Type**: One-time payment
- **Price**: `$29.99`
- **Currency**: USD
- **Description**: `200 credits - Great for regular creators`
- **Stock Limit**: Unlimited
- **Visibility**: Visible

### Package 3: Professional Pack
- **Product Name**: `Mynted AI - Professional Pack`
- **Pricing Type**: One-time payment
- **Price**: `$59.99`
- **Currency**: USD
- **Description**: `500 credits - For serious professionals`
- **Stock Limit**: Unlimited
- **Visibility**: Visible

### Package 4: Enterprise Pack
- **Product Name**: `Mynted AI - Enterprise Pack`
- **Pricing Type**: One-time payment
- **Price**: `$199.99`
- **Currency**: USD
- **Description**: `2000 credits - Maximum value for power users`
- **Stock Limit**: Unlimited
- **Visibility**: Visible

### Payment Methods
Enable these for all products:
- ✅ Credit/debit card
- ✅ PayPal
- ✅ Bank transfer (ACH)
- ✅ Cryptocurrency (optional)

---

## STEP 3: SETUP WEBHOOKS

### Navigate to Webhooks
1. Go to https://whop.com/dashboard/biz_7iDflJsY9KDdBY/
2. Click **Developer** tab in left sidebar
3. Click **Create Webhook**

### Webhook Configuration
**Webhook URL**: `https://your-bot-domain.railway.app/webhooks/whop`
(You'll need to deploy the webhook endpoint first - see Step 4)

**Events to Subscribe**:
- ✅ `payment.succeeded` (CRITICAL - triggers credit addition)
- ✅ `payment.failed`
- ✅ `membership.activated`
- ✅ `refund.created`

**Save the Webhook Secret**: You'll get a webhook secret - save it as `WHOP_WEBHOOK_SECRET` environment variable

---

## STEP 4: INTEGRATE WHOP WITH YOUR BOT

### Add Environment Variables to Railway

Run these commands:
```bash
railway variables --set "WHOP_API_KEY=apik_w2L2JAbWdkh08_C4124204_C_0fcdcad7c9f48b972289ab554553ca4d7cdb49e74118450676974d40fa495d"
railway variables --set "WHOP_WEBHOOK_SECRET=<your-webhook-secret-from-step-3>"
railway variables --set "WHOP_COMPANY_ID=biz_7iDflJsY9KDdBY"
```

### Credit Package Mapping
Add this to map Whop product IDs to credit amounts:
```bash
railway variables --set "WHOP_STARTER_PRODUCT_ID=<product-id-from-whop>"
railway variables --set "WHOP_STARTER_CREDITS=50"

railway variables --set "WHOP_CREATOR_PRODUCT_ID=<product-id-from-whop>"
railway variables --set "WHOP_CREATOR_CREDITS=200"

railway variables --set "WHOP_PROFESSIONAL_PRODUCT_ID=<product-id-from-whop>"
railway variables --set "WHOP_PROFESSIONAL_CREDITS=500"

railway variables --set "WHOP_ENTERPRISE_PRODUCT_ID=<product-id-from-whop>"
railway variables --set "WHOP_ENTERPRISE_CREDITS=2000"
```

---

## STEP 5: UPDATE BOT CODE

The webhook handler code has been added to your bot (see `src/services/whop_handler.py`).

Deploy the updated bot:
```bash
cd /Users/poghos/Desktop/Creative/mynted-bot
railway up --detach
```

---

## STEP 6: TEST THE INTEGRATION

### Test Purchase Flow
1. Go to your Whop store page
2. Purchase the Starter Pack ($9.99) using test mode
3. Check if credits are added to your Discord account
4. Run `/balance` in Discord to verify

### Check Webhook Logs
```bash
railway logs
```

Look for:
- "Received Whop webhook: payment.succeeded"
- "Added X credits to user Y"

---

## STEP 7: UPDATE /BUY COMMAND

The `/buy` command needs to link to your Whop checkout URLs.

After creating products, get the checkout URLs:
1. Go to each product in Whop dashboard
2. Click "View" or "Share"
3. Copy the checkout URL (looks like: `https://whop.com/checkout/plan_xxxxx`)

Add these URLs to the `/buy` command embeds in `src/cogs/general.py`

---

## TROUBLESHOOTING

### Webhook Not Receiving Events
- Verify webhook URL is publicly accessible (not localhost)
- Check Railway logs for incoming requests
- Ensure webhook secret is correctly set in environment variables

### Credits Not Adding
- Check Railway logs for errors
- Verify product ID mapping in environment variables
- Confirm database connection is working

### Payment Failed
- Check Whop dashboard for payment status
- Verify payment method is enabled
- Check for currency/region restrictions

---

## NEXT STEPS

1. ✅ Create 4 products in Whop dashboard
2. ✅ Set up webhook endpoint
3. ✅ Deploy bot with webhook handler
4. ✅ Test with a real purchase
5. ✅ Update `/buy` command with checkout URLs
6. ✅ Create promotional materials for your Whop store
7. ✅ Set up Discord role sync (optional - for premium users)

---

## USEFUL LINKS

- **Whop Dashboard**: https://whop.com/dashboard/biz_7iDflJsY9KDdBY/
- **Whop Developer Docs**: https://docs.whop.com/developer/guides/webhooks
- **Railway Dashboard**: https://railway.com/project/5604b7a8-d850-49df-8813-ce34995c0f5f
- **Bot Repository**: https://github.com/BoghosKar/mynted-bot

---

## SUPPORT

If you need help:
- Whop Support: https://help.whop.com/
- Railway Support: https://railway.com/help
- Discord.py Docs: https://docs.pycord.dev/
