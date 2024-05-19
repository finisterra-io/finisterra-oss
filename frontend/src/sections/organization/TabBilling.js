import { useEffect, useState } from "react";
import { useSelector, useDispatch } from "store"; // Make sure you import useDispatch correctly
import { getUsageAndSubscriptionStatus, getUsage } from "store/reducers/usage";
import { useSnackbar } from "notistack";
import { loadStripe } from "@stripe/stripe-js";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from "@mui/material";

import {
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import MainCard from "components/MainCard";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY);

const TabBilling = () => {
  const { usage, hasActiveSubscription } = useSelector((state) => state.usage);
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [openCancelDialog, setOpenCancelDialog] = useState(false);

  useEffect(() => {
    dispatch(getUsageAndSubscriptionStatus());
    dispatch(getUsage());
  }, []);

  const showCancelDialog = () => setOpenCancelDialog(true);
  const closeCancelDialog = () => setOpenCancelDialog(false);

  const handleStartSubscription = async () => {
    setLoading(true);

    try {
      const stripe = await stripePromise;
      // Call to backend API to start the subscription
      const response = await fetch("/api/billing/start-subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const { sessionId } = await response.json();
        // Redirect to Stripe Checkout
        const { error } = await stripe.redirectToCheckout({ sessionId });
        if (error) throw new Error(error.message);
      } else {
        throw new Error("Failed to start subscription");
      }
    } catch (error) {
      enqueueSnackbar(error.message, { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    setLoading(true);
    try {
      // Call to backend API to cancel the subscription
      const response = await fetch("/api/billing/cancel-subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        enqueueSnackbar("Subscription cancelled successfully", {
          variant: "success",
        });
        dispatch(getUsageAndSubscriptionStatus()); // Refresh to update the UI accordingly
      } else {
        throw new Error("Failed to cancel subscription");
      }
    } catch (error) {
      enqueueSnackbar(error.message, { variant: "error" });
    } finally {
      setLoading(false);
      closeCancelDialog();
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} display="flex" justifyContent="flex-end">
        {!hasActiveSubscription ? (
          <Button
            variant="contained"
            color="primary"
            onClick={handleStartSubscription}
            disabled={loading}
          >
            Start Subscription
          </Button>
        ) : (
          ""
        )}
      </Grid>
      <Grid item xs={12}>
        <MainCard title="Usage" content={false}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ pl: 3 }}>Provider</TableCell>
                <TableCell sx={{ pl: 3 }}>Accounts</TableCell>
                <TableCell sx={{ pl: 3 }}>Price</TableCell>
                <TableCell sx={{ pl: 3 }}>Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {usage.map((key) => (
                <TableRow hover key={key.provider}>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">{key.provider}</Typography>
                  </TableCell>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">{key.accounts}</Typography>
                  </TableCell>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">
                      {key.price.toLocaleString("en-US", {
                        style: "currency",
                        currency: "USD",
                      })}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">
                      {(key.accounts * key.price).toLocaleString("en-US", {
                        style: "currency",
                        currency: "USD",
                      })}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </MainCard>
      </Grid>

      <Grid item xs={12} display="flex" justifyContent="flex-end">
        {hasActiveSubscription ? (
          <Button
            variant="contained"
            color="error"
            onClick={showCancelDialog} // Open dialog
            disabled={loading}
          >
            Cancel Subscription
          </Button>
        ) : (
          ""
        )}
      </Grid>
      <Dialog
        open={openCancelDialog}
        onClose={closeCancelDialog}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {"Confirm Subscription Cancellation"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Are you sure you want to cancel your subscription?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            variant="contained"
            onClick={closeCancelDialog}
            color="primary"
          >
            Close
          </Button>
          <Button
            variant="contained"
            onClick={handleCancelSubscription}
            color="error"
            autoFocus
          >
            Continue
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  );
};

export default TabBilling;
