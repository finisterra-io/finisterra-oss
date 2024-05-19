import { createSlice } from "@reduxjs/toolkit";

// project import
import axios from "utils/axios";
import { dispatch } from "store";

import { openSnackbar } from "store/reducers/snackbar";

const initialState = {
  error: false,
  usage: [],
  hasActiveSubscription: false,
  isLoader: false,
};

// ==============================|| BILLING - SLICE ||============================== //

const usage = createSlice({
  name: "usage",
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

    // Usage list
    setUsage(state, action) {
      state.isLoader = false;
      state.usage = action.payload;
    },

    setUsageSubscriptionStatus(state, action) {
      state.isLoader = false;
      state.hasActiveSubscription = action.payload;
    },

    // create Usage
    createUsage(state, action) {
      const newUsage = action.payload;
      state.isLoader = false;
      if (newUsage.new !== false) {
        state.usage = [...state.usage, newUsage];
      }
    },

    // delete event
    deleteUsage(state, action) {
      const id = action.payload;
      state.usage = state.usage.filter((key) => key.id !== id);
    },
  },
});

export default usage.reducer;
export function getUsage() {
  return async () => {
    dispatch(usage.actions.loading());
    try {
      const response = await axios.get("/api/billing/usage");

      // Check if usage is undefined and if so, default to an empty array
      const usageData = response.data.usage || [];

      dispatch(usage.actions.setUsage(usageData));
    } catch (error) {
      dispatch(usage.actions.hasError(error));
    }
  };
}

// In your usage action/reducer file
export const getUsageAndSubscriptionStatus = () => async (dispatch) => {
  try {
    const subscriptionResponse = await fetch(
      "/api/billing/subscription-status"
    );
    const subscriptionData = await subscriptionResponse.json();
    console.log(subscriptionData);

    dispatch(
      usage.actions.setUsageSubscriptionStatus(
        subscriptionData.hasActiveSubscription
      )
    );
  } catch (error) {
    dispatch(usage.actions.hasError(error));
  }
};

export function createUsage(newUsage) {
  return async () => {
    dispatch(usage.actions.loading());
    try {
      const response = await axios.post("/api/usage/usage", newUsage);
      dispatch(usage.actions.createUsage(response.data.createdUsage));
      dispatch(
        openSnackbar({
          open: true,
          message: "Usage created successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(usage.actions.hasError(error.error));
      dispatch(
        openSnackbar({
          open: true,
          message: "Something went wrong.",
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

export function deleteUsage(deletedUsage) {
  return async () => {
    dispatch(usage.actions.loading());

    try {
      await axios.delete(`/api/usage/usage?id=${deletedUsage}`);
      dispatch(usage.actions.deleteUsage(deletedUsage));
      dispatch(
        openSnackbar({
          open: true,
          message: "Usage deleted successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(usage.actions.hasError(error));
      dispatch(
        openSnackbar({
          open: true,
          message: "Something went wrong.",
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
