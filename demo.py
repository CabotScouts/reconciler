from reconciler import Reconciler

if __name__ == "__main__" :
    r = Reconciler(
        gc    = {
            "token" : ""
        },
        mail  = {
            "driver" : "mailgun",
            "api"    : "",
            "key"    : "",
            "domain" : "",
            "from"   : "A Name <email@address.org.uk>",
            "to"     : ["treasurer@address.org.uk"]
        },
        limit = "finyear",
        file  = "payments.xlsx"
    )

    r.reconcile()
    r.export()
