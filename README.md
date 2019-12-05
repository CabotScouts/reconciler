# reconciler
Util for reconciling GoCardless payments and payouts

Will match a *payout* into your bank account, with the *payments* from parents that it consists of (so these can then be properly reconciled)

## Required packages
* **gocardless_pro** - GoCardless API
* **openpyxl** - for writing xlsx files
* *requests* - if using Mailgun mail driver

## Parameters
Required parameters in bold
* **gc** - (dict) GoCardless options
  * **token** - access token, must have read access
  * *environment* - environment being used (if omitted defaults to 'live')
* *mail* - (dict) Settings for sending exported payments by mail
  * **driver** - which mail driver to use (currently only 'mailgun' works)
  * *driver specific options* - see below
* *limit* - (string) how far back to fetch payouts, one of:
  * week
  * month
  * year
  * finyear
  * all
* *file* - (string) what to call the exported xlsx file (defaults to 'export.xlsx')
