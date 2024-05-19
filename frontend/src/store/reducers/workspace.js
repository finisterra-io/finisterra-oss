import { createSlice } from "@reduxjs/toolkit";

// project import
import axios from "utils/axios";
import { dispatch } from "store";

import { openSnackbar } from "store/reducers/snackbar";

const initialState = {
  error: false,
  workspaces: [],
  isLoader: false,
};

// ==============================|| CALENDAR - SLICE ||============================== //

const workspace = createSlice({
  name: "workspace",
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

    // Workspace list
    setWorkspaces(state, action) {
      state.isLoader = false;
      state.workspaces = action.payload;
    },

    // create Workspace
    createWorkspace(state, action) {
      const newWorkspace = action.payload;
      state.isLoader = false;
      state.workspaces = [...state.workspaces, newWorkspace];
    },

    // update Workspace
    updateWorkspace(state, action) {
      const workspace = action.payload;
      const workspaceUpdate = state.workspaces.map((item) => {
        if (item.id === workspace.id) {
          return workspace;
        }
        return item;
      });

      state.isLoader = false;
      state.workspaces = workspaceUpdate;
    },

    // delete event
    deleteWorkspace(state, action) {
      const id = action.payload;
      state.workspaces = state.workspaces.filter(
        (workspace) => workspace.id !== id
      );
    },
  },
});

export default workspace.reducer;

export function getWorkspaces(awsAccountId) {
  return async (dispatch) => {
    dispatch(workspace.actions.loading());
    try {
      // Add awsAccountId to the query parameters of the request
      const response = await axios.get("/api/workspace/workspace", {
        params: {
          awsAccountId: awsAccountId,
        },
      });

      dispatch(workspace.actions.setWorkspaces(response.data.workspaces));
    } catch (error) {
      dispatch(workspace.actions.hasError(error));
    }
  };
}

export function createWorkspace(newWorkspace) {
  return async () => {
    dispatch(workspace.actions.loading());
    try {
      const response = await axios.post(
        "/api/workspace/workspace",
        newWorkspace
      );
      dispatch(workspace.actions.createWorkspace(response.data.newWorkspace));
      dispatch(
        openSnackbar({
          open: true,
          message: "Workspace added successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(workspace.actions.hasError(error.error));
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

export function updateWorkspace(updatedAwsWorkspace) {
  return async () => {
    dispatch(workspace.actions.loading());
    try {
      const response = await axios.put(
        "/api/workspace/workspace",
        updatedAwsWorkspace
      );
      dispatch(
        workspace.actions.updateWorkspace(response.data.updatedWorkspace)
      );
      dispatch(
        openSnackbar({
          open: true,
          message: "Workspace updated successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(workspace.actions.hasError(error));
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

export function deleteWorkspace(id) {
  return async () => {
    dispatch(workspace.actions.loading());
    try {
      await axios.delete(`/api/workspace?id=${id}`);
      dispatch(workspace.actions.deleteWorkspace(id));
      dispatch(
        openSnackbar({
          open: true,
          message: "Workspace deleted successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(workspace.actions.hasError(error));
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
