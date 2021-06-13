# Reconciler
Package for reconciling GoCardless payments and payouts and exporting to xlsx.

Will match a *payout* to a bank account, with the *payments* that it consists of (so these can then be properly reconciled).

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
  * **driver** - (string) which mail driver to use
  * **from** - (string) the address to send from, in the format `Name <email@address.org>`
  * *to* - (list) a list of email addresses to send the exported xlsx file to
  * *cc* - (list) a list of email addresses to cc the exported xlsx file to
  * *bcc* - (list) a list of email addresses to bcc the exported xlsx file to
  * *driver specific parameters* - depend on the driver you're using - see below
* *limit* - (string) how far back to fetch payouts, one of:
  * week
  * month - default
  * year
  * finyear (all payments in the current financial year)
  * calyear (all payments in the current calendar year)
  * all (this does work but can be a bit slow if you've been using GoCardless for a while)
* *file* - (string) what to call the exported xlsx file (defaults to 'gocardless_<date>.xlsx')
* *columns* - (list) payout/payment keys to use in custom xlsx columns (see below)
* *headings* - (list) headings for these custom columns
* *parser* - (function handle) a custom payment description parsing function (see below)
* *vat* - (boolean) whether VAT should be charged on the GC fee after 01/09/2020 (default True)

## Fee Calculations
Fees charged by GoCardless and OSM are manually calculated by the reconciler, as they cannot be obtained through the GoCardless API.

* GoCardless fee - 1% of the charged amount, minimum 15p
* GoCardless fee VAT - 20% VAT on the above GoCardless fee, minimum 3p (from 01/09/2020)
* OSM fee - 1.95% of the charged amount


## Methods
* `Reconciler(parameters)` - Reconciler object, takes in keyword argument config parameters
* `.reconcile()` - performs the reconciliation
* `.export()` - exports the reconciled payments into an xlsx file
* `.send()` - sends out an exported xlsx via email

## Mail Drivers
Currently SMTP and Mailgun are supported. If you use another mail API you'll need to make your own driver for this (or ask nicely and I'll have a look).

### SMTP
Parameters:
* **hostname** - (string) SMTP server hostname
* *port* - (int) SMTP server port - defaults to 25 if not specified
* **username** - (string)
* **password** - (string)
* *ssl* - (boolean) whether to send with SSL or not

### Mailgun
Parameters:

* **api** - (string) api endpoint
* **key** - (string) your secret key
* **domain** - (string) the domain you have setup to send mail from

## Customising Exported Data
### Custom XLSX columns
By supplying a list of column names, the exported xlsx can be customised. Custom column headers can also be supplied in the same way (just make sure the headings and custom columns lists match up!).

Possible values:

* payout_id
* payout_date - when GoCardless paid out the money
* payout_reference - the bank reference GoCardless will have used
* payment_id
* payment_date - when the payment was received by GoCardless
* payment_amount_gross - the amount paid in
* payment_amount_net - the amount paid out by GoCardless (with GoCardless/OSM fees taken)
* payment_amount_fees - the fees charged on the payment by GoCardless and OSM
* payment_description - the payment description (a combination of the payment schedule and activity)
* payment_description_schedule - payment schedule, parsed from the description
* payment_description_event - payment event, parsed from the description
* *other values returned by custom description parser*

### Custom Payment Description Parsing
The payment description given by OSM is made up of the payment schedule, and the activity or term (in the format `<schedule> (<activity>)`). Depending on how your schedules are named, there might be additional information included (in our case the schedules also include the ESU name) - by specifying a custom parser function and passing a handle for this using the `parser` parameter, this information can be extracted.

The function must take a single argument (the payment description string), and return a dict - these keys can then be specified as custom columns.

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
