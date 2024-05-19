import { createSlice } from "@reduxjs/toolkit";

// project import
import axios from "utils/axios";
import { dispatch } from "store";

import { openSnackbar } from "store/reducers/snackbar";

const initialState = {
  error: false,
  members: [],
  isLoader: false,
};

// ==============================|| CALENDAR - SLICE ||============================== //

const member = createSlice({
  name: "member",
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

    // Member list
    setMembers(state, action) {
      state.isLoader = false;
      state.members = action.payload;
    },

    // create Member
    createMember(state, action) {
      const newMember = action.payload;
      state.isLoader = false;
      state.members = [...state.members, newMember];
    },

    // update Member
    updateMember(state, action) {
      const invitation = action.payload;
      const invitationUpdate = state.members.map((item) => {
        if (item.id === invitation.id) {
          return invitation;
        }
        return item;
      });

      state.isLoader = false;
      state.members = invitationUpdate;
    },

    // delete event
    deleteMember(state, action) {
      const id = action.payload;
      state.members = state.members.filter(
        (invitation) => invitation.id !== id
      );
    },
  },
});

export default member.reducer;

export function getMembers() {
  return async () => {
    dispatch(member.actions.loading());
    try {
      const response = await axios.get("/api/organization/member");
      dispatch(member.actions.setMembers(response.data.members));
    } catch (error) {
      dispatch(member.actions.hasError(error));
    }
  };
}

export function createMember(newMember) {
  return async () => {
    dispatch(member.actions.loading());
    try {
      const response = await axios.post(
        "/api/organization/invitation",
        newMember
      );
      dispatch(member.actions.createMember(response.data.invitation));
      dispatch(
        openSnackbar({
          open: true,
          message: "Inivitation sent successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(member.actions.hasError(error.error));
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

export function updateMember(updatedMember) {
  return async () => {
    dispatch(member.actions.loading());
    try {
      const response = await axios.put(
        "/api/organization/invitation",
        updatedMember
      );
      dispatch(member.actions.updateMember(response.data.updatedAccount));
      dispatch(
        openSnackbar({
          open: true,
          message: "Member updated successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(member.actions.hasError(error));
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

export function deleteMember(deletedMember) {
  const id = deletedMember.id;
  return async () => {
    dispatch(member.actions.loading());

    try {
      await axios.delete(`/api/organization/member?id=${id}`);
      if (deletedMember.status == "PENDING") {
        dispatch(member.actions.deleteMember(id));
      } else {
        const deletedMemberCopy = { ...deletedMember, status: "INACTIVE" };
        dispatch(member.actions.updateMember(deletedMemberCopy));
      }
      dispatch(
        openSnackbar({
          open: true,
          message: "Member deleted successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(member.actions.hasError(error));
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

export function activateMember(updatedMember) {
  const id = updatedMember.id;
  return async () => {
    dispatch(member.actions.loading());
    try {
      const response = await axios.put(`/api/organization/member?id=${id}`);
      const updatedMemberCopy = { ...updatedMember, status: "ACTIVE" };
      dispatch(member.actions.updateMember(updatedMemberCopy));
      dispatch(
        openSnackbar({
          open: true,
          message: "Member activated successfully.",
          variant: "alert",
          alert: {
            color: "success",
          },
          close: true,
        })
      );
    } catch (error) {
      dispatch(member.actions.hasError(error));
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
