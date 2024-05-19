import { createSlice } from "@reduxjs/toolkit";

// project import
import axios from "utils/axios";
import { dispatch } from "store";

import { openSnackbar } from "store/reducers/snackbar";

const initialState = {
  error: false,
  accounts: [],
  enabledAccounts: 0,
  isLoader: false,
};

// ==============================|| AWS ACCOUNT - SLICE ||============================== //

const awsAccount = createSlice({
  name: "awsAccount",
  initialState,
  reducers: {
    // loader
    loading(state) {
      state.isLoader = true;
    },

    // error
    hasError(state, action) {
      state.isLoader = false;
      state.error = action.payload;
    },

    // AWSAccount list
    setAWSAccounts(state, action) {
      state.isLoader = false;
      state.accounts = action.payload;
      state.enabledAccounts = action.payload.filter(
        (account) => account.enabled === true
      ).length;
    },

    setUsageSubscriptionStatus(state, action) {
      state.isLoader = false;
      state.hasActiveSubscription = action.payload;
    },

    // create AWSAccount
    createAWSAccount(state, action) {
      const newAWSAccount = action.payload;
      state.isLoader = false;
      state.accounts = [...state.accounts, newAWSAccount];
    },

    // update AWSAccount
    updateAWSAccount(state, action) {
      const account = action.payload;
      const accountUpdate = state.accounts.map((item) => {
        console.log(item);
        if (item.id === account.id) {
          return account;
        }
        return item;
      });

      state.isLoader = false;
      state.accounts = accountUpdate;
    },

    // delete event
    deleteAWSAccount(state, action) {
      const id = action.payload;
      state.accounts = state.accounts.filter((account) => account.id !== id);
    },
  },
});

export default awsAccount.reducer;

export function getAWSAccounts() {
  return async () => {
    dispatch(awsAccount.actions.loading());
    try {
      const response = await axios.get("/api/aws/account");
      dispatch(awsAccount.actions.setAWSAccounts(response.data.accounts));
    } catch (error) {
      dispatch(awsAccount.actions.hasError(error));
    }
  };
}

export function createAWSAccount(newAWSAccount) {
  return async (dispatch) => {
    dispatch(awsAccount.actions.loading());
    try {
      const response = await axios.post("/api/aws/account", newAWSAccount);
      return Promise.resolve(response.data.newAccount);
    } catch (error) {
      dispatch(awsAccount.actions.hasError(error.error));
      dispatch(
        openSnackbar({
          open: true,
          message: error.error,
          variant: "alert",
          alert: {
            color: "error",
          },
          close: true,
        })
      );
      return Promise.reject(error.error);
    }
  };
}

export function updateAWSAccount(updatedAwsAccount) {
  return async () => {
    dispatch(awsAccount.actions.loading());
    try {
      const response = await axios.put("/api/aws/account", updatedAwsAccount);
      // dispatch(
      //   awsAccount.actions.updateAWSAccount(response.data.updatedAccount)
      // );
      dispatch(
        openSnackbar({
          open: true,
          message: "AWS Account updated successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
      return Promise.resolve(response.data.updatedAccount);
    } catch (error) {
      dispatch(awsAccount.actions.hasError(error));
      dispatch(
        openSnackbar({
          open: true,
          message: error.error,
          variant: "alert",
          alert: {
            color: "error",
          },
          close: true,
        })
      );
      return Promise.reject(error.error);
    }
  };
}

export function deleteAWSAccount(id) {
  return async () => {
    dispatch(awsAccount.actions.loading());
    try {
      await axios.delete(`/api/aws/account?id=${id}`);
      dispatch(awsAccount.actions.deleteAWSAccount(id));
      dispatch(
        openSnackbar({
          open: true,
          message: "AWS Account deleted successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(awsAccount.actions.hasError(error));
      dispatch(
        openSnackbar({
          open: true,
          message: error.error,
          variant: "alert",
          alert: {
            color: "error",
          },
          close: true,
        })
      );
    }
  };
}
