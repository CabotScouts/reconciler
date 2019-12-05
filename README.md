# reconciler
Util for reconciling GoCardless payments and payouts

Will match a *payout* with the *payments* that it consists of (so these can be properly reconciled)

Uses Mailgun to send emails - if you use a different API you'll need to modify this to use that

## Needed packages
* gocardless_pro (GoCardless API)
* requests (for sending emails)
* openpyxl (for writing xlsx files)
