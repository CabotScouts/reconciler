from reconciler import Reconciler

if __name__ == "__main__" :
    r = Reconciler(
        gc    = {
            "token" : ""
        },
        limit = "finyear",
        file  = "payments.xlsx"
    )

    r.reconcile()
    r.export()
