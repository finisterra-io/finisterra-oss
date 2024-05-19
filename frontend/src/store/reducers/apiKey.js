import { createSlice } from "@reduxjs/toolkit";

// project import
import axios from "utils/axios";
import { dispatch } from "store";

import { openSnackbar } from "store/reducers/snackbar";

const initialState = {
  error: false,
  apiKeys: [],
  isLoader: false,
};

// ==============================|| CALENDAR - SLICE ||============================== //

const apiKey = createSlice({
  name: "apiKey",
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

    // ApiKey list
    setApiKeys(state, action) {
      state.isLoader = false;
      state.apiKeys = action.payload;
    },

    // create ApiKey
    createApiKey(state, action) {
      const newApiKey = action.payload;
      state.isLoader = false;
      if (newApiKey.new !== false) {
        state.apiKeys = [...state.apiKeys, newApiKey];
      }
    },

    // delete event
    deleteApiKey(state, action) {
      const id = action.payload;
      state.apiKeys = state.apiKeys.filter((key) => key.id !== id);
    },
  },
});

export default apiKey.reducer;
export function getApiKeys() {
  return async () => {
    dispatch(apiKey.actions.loading());
    try {
      const response = await axios.get("/api/api-key/api-key");

      // Check if apiKeys is undefined and if so, default to an empty array
      const apiKeysData = response.data.apiKeys || [];

      dispatch(apiKey.actions.setApiKeys(apiKeysData));
    } catch (error) {
      dispatch(apiKey.actions.hasError(error));
    }
  };
}

export function createApiKey(newApiKey) {
  return async () => {
    dispatch(apiKey.actions.loading());
    try {
      const response = await axios.post("/api/api-key/api-key", newApiKey);
      dispatch(apiKey.actions.createApiKey(response.data.createdApiKey));
      dispatch(
        openSnackbar({
          open: true,
          message: "ApiKey created successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(apiKey.actions.hasError(error.error));
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

export function deleteApiKey(deletedApiKey) {
  return async () => {
    dispatch(apiKey.actions.loading());

    try {
      await axios.delete(`/api/api-key/api-key?id=${deletedApiKey}`);
      dispatch(apiKey.actions.deleteApiKey(deletedApiKey));
      dispatch(
        openSnackbar({
          open: true,
          message: "ApiKey deleted successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(apiKey.actions.hasError(error));
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
