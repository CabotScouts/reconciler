from reconciler import Reconciler

if __name__ == "__main__":
    r = Reconciler(
        gc={"token": ""},
        limit="finyear",
    )

    r.reconcile()
    r.export()
