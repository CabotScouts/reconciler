# Reconciler
Util for reconciling GoCardless payments and payouts, and exporting these

Will match a *payout* to your bank account, with the *payments* that it consists of (so these can then be properly reconciled).

## Required packages
* **gocardless_pro** - GoCardless API
* **openpyxl** - for writing xlsx files
* *requests* - if using Mailgun mail driver

## Parameters
Those in bold are required.

* **gc** - (dict) GoCardless options
  * **token** - access token, must have read access
  * *environment* - environment being used (if omitted defaults to 'live')
* *mail* - (dict) Settings for sending exported payments by mail
  * **driver** - (string) which mail driver to use (currently only 'mailgun' works)
  * **from** - (string) the address to send from, in the format `Name <email@address.org>`
  * *to* - (list) a list of email addresses to send the exported xlsx file to
  * *cc* - (list) a list of email addresses to cc the exported xlsx file to
  * *bcc* - (list) a list of email addresses to bcc the exported xlsx file to
  * *driver specific parameters* - depend on the driver you're using - see below
* *limit* - (string) how far back to fetch payouts, one of:
  * week
  * month
  * year
  * finyear (all payments in current financial year)
  * all (if you've been using GoCardless for a while this might break?)
* *file* - (string) what to call the exported xlsx file (defaults to 'export.xlsx')
* *columns* - (list) the payout/payment attributes to use in xlsx columns (see below)
* *headings* - (list) column headings for the xlsx file
* *parser* - (function handle) a custom payment description parsing function (see below)

## Methods
* `Reconciler(parameters)` - Reconciler object, takes a dict of config parameters 
* `.reconcile()` - performs the reconciliation
* `.export()` - exports the reconciliated payments into an xlsx file
* `.send()` - sends out an exported xlsx via email

## Mail Drivers
Currently only Mailgun is supported - will look at SMTP soon. If you use another mail API you'll need to make your own driver for this (or ask nicely and I'll have a look).

### SMTP
Coming soon!

### Mailgun
Parameters:

* **api** - (string) api endpoint (will probably be the EU address)
* **key** - (string) your secret key
* **domain** - (string) the domain you have setup to send mail from

## Customising `Reconciler` Export
### Custom XLSX columns
By supplying a list of column names, the exported xlsx can be customised. Custom headers can also be supplied in the same way (just make sure the two lists are the same length).

Possible values:

* payout_id
* payout_date - when GoCardless paid out the money
* payout_reference - the bank reference GoCardless will have used
* payment_id
* payment_date - when the payment was received by GoCardless
* payment_amount_gross - the amount paid in
* payment_amount_net - the amount paid out by GoCardless (with GoCardless/OSM fees taken)
* payment_description - the payment description (a combination of the payment schedule and activity)
* *other values returned by custom description parser*

### Custom Payment Description Parsing
The payment description given by OSM is made up of the payment schedule, and the activity or term (in the format `<schedule> (<activity>)`). Depending on how your schedules are named, there might be additional information included (in our case the schedules also include the ESU name) - by specifying a custom parsing function and passing a handle for this using the `parser` parameter, this information can be extracted.

The function must take a single argument (the payment description string), and return a dict - these keys can then be specified in the custom column list (above).

#### Example Custom Parser
```python
def parseDescription(description) :
    pattern = re.compile("([\w\W]+) ESU ([\w\W]+) \(([\w\W]+)\)")
    match = pattern.findall(description)
    match = match[0] if (len(match) > 0) else ["", "", ""]

    return {
        "payment_description_unit"     : match[0],
        "payment_description_schedule" : match[1],
        "payment_description_event"    : match[2]
    }
```
