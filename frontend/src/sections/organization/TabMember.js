import axios from "utils/axios";

import { useState, useEffect } from "react";
import { MenuItem } from "@mui/material";

import { openSnackbar } from "store/reducers/snackbar";

import { Formik, Form, Field, ErrorMessage } from "formik";
import * as Yup from "yup";

// material-ui
import {
  Button,
  Chip,
  Grid,
  InputLabel,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import IconButton from "components/@extended/IconButton";

// project import
import MainCard from "components/MainCard";
import Avatar from "components/@extended/Avatar";

import { dispatch, useSelector } from "store";
import {
  getMembers,
  createMember,
  deleteMember,
  activateMember,
} from "store/reducers/member";

// assets
import { EllipsisOutlined, DeleteOutlined } from "@ant-design/icons";

// table data
function createData(name, avatar, email, role, status) {
  return { name, avatar, email, role, status };
}

// ==============================|| ACCOUNT PROFILE - ROLE ||============================== //

const TabMember = () => {
  const { members } = useSelector((state) => state.member);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [activateModalOpen, setActivateModalOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);

  useEffect(() => {
    dispatch(getMembers());
    // console.log("members", members);
  }, []);

  const handleSend = async (values, { resetForm }) => {
    const emailExists = members.some((member) => member.email === values.email);
    if (emailExists) {
      dispatch(
        openSnackbar({
          open: true,
          message: "User is already a member or has a pending invitation.",
          variant: "alert",
          alert: {
            color: "warning",
          },
          close: true,
        })
      );
    } else {
      dispatch(createMember(values));
      resetForm();
    }
  };

  const confirmDeleteMember = async () => {
    // Call the delete API here
    dispatch(deleteMember(selectedMember));

    // Close the modal
    setDeleteModalOpen(false);
  };

  const cancelDeleteMember = () => {
    setSelectedMember(null);
    setDeleteModalOpen(false);
  };

  const handleDeleteMember = (row) => {
    if (row.role === "OWNER") {
      dispatch(
        openSnackbar({
          open: true,
          message: "You cannot delete the OWNER member.",
          variant: "alert",
          alert: {
            color: "warning",
          },
          close: true,
        })
      );
      return;
    }
    setSelectedMember(row);
    setDeleteModalOpen(true);
  };

  const confirmActivateMember = async () => {
    // Call the delete API here
    dispatch(activateMember(selectedMember));

    // Close the modal
    setActivateModalOpen(false);
  };

  const cancelActivateMember = () => {
    setSelectedMember(null);
    setActivateModalOpen(false);
  };

  const handleActivateMember = async (row) => {
    setSelectedMember(row);
    setActivateModalOpen(true);
  };

  const handleResendInvitation = async (email) => {
    try {
      const response = await axios.post("/api/organization/invitation", {
        email: email,
      });
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

  const validationSchema = Yup.object().shape({
    email: Yup.string()
      .email("Invalid email address")
      .required("Email address is required"),
  });

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <MainCard title="Invite Team Members" content={false}>
          <Stack spacing={2.5} sx={{ p: 2.5 }}>
            <Formik
              initialValues={{ email: "", role: "MEMBER" }}
              validationSchema={validationSchema}
              onSubmit={handleSend}
            >
              {({ isSubmitting, isValid }) => (
                <Form>
                  <Stack
                    spacing={3}
                    direction="row"
                    justifyContent="space-between"
                    alignItems="flex-start"
                    sx={{ width: "100%", flexWrap: "nowrap" }}
                  >
                    <Stack spacing={1} sx={{ flexGrow: 1, mr: 2 }}>
                      <InputLabel
                        htmlFor="outlined-email"
                        sx={{ paddingTop: "0.2rem" }}
                      >
                        Email Address
                      </InputLabel>
                      <Field
                        as={TextField}
                        fullWidth
                        id="outlined-email"
                        name="email"
                        variant="outlined"
                        placeholder="Enter the email address"
                      />
                      <div style={{ height: "1.2rem" }}>
                        <ErrorMessage name="email">
                          {(msg) => (
                            <Typography variant="caption" color="error">
                              {msg}
                            </Typography>
                          )}
                        </ErrorMessage>
                      </div>
                    </Stack>
                    <Stack spacing={1} sx={{ flexGrow: 1, mr: 2 }}>
                      <InputLabel
                        htmlFor="outlined-role"
                        sx={{
                          paddingTop: "0.2rem",
                        }}
                      >
                        Role
                      </InputLabel>
                      <Field
                        as={TextField}
                        fullWidth
                        id="outlined-role"
                        name="role"
                        select
                        variant="outlined"
                      >
                        <MenuItem value="ADMIN">Admin</MenuItem>
                        <MenuItem value="MEMBER">Member</MenuItem>
                      </Field>
                    </Stack>
                    <Button
                      variant="contained"
                      size="large"
                      type="submit"
                      disabled={isSubmitting || !isValid}
                      sx={{
                        alignSelf: "center",
                      }}
                    >
                      Send
                    </Button>
                  </Stack>
                </Form>
              )}
            </Formik>
          </Stack>
          <TableContainer>
            <Table sx={{ minWidth: 350 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ pl: 3 }}>Member</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell align="right">Status</TableCell>
                  <TableCell align="right" />
                </TableRow>
              </TableHead>
              <TableBody>
                {members.map((row) => (
                  <TableRow hover key={row.email}>
                    <TableCell sx={{ pl: 3 }} component="th">
                      <Stack direction="row" alignItems="center" spacing={1.25}>
                        <Stack spacing={0}>
                          <Typography variant="subtitle1">
                            {row.name}
                          </Typography>
                          <Typography variant="caption" color="secondary">
                            {row.email}
                          </Typography>
                        </Stack>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {row.role === "OWNER" && (
                        <Chip size="small" color="primary" label={row.role} />
                      )}
                      {row.role === "MEMBER" && (
                        <Chip
                          size="small"
                          variant="light"
                          color="info"
                          label={row.role}
                        />
                      )}
                      {row.role === "ADMIN" && (
                        <Chip
                          size="small"
                          variant="light"
                          color="warning"
                          label={row.role}
                        />
                      )}
                      {row.role === 0 && (
                        <Chip
                          size="small"
                          variant="light"
                          color="success"
                          label="Customer"
                        />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {row.status === "PENDING" && (
                        <Stack
                          direction="row"
                          alignItems="center"
                          spacing={1.25}
                          justifyContent="flex-end"
                        >
                          <Button
                            size="small"
                            color="error"
                            onClick={() => handleResendInvitation(row.email)}
                          >
                            Resend
                          </Button>
                          <Chip
                            size="small"
                            color="info"
                            variant="outlined"
                            label="INVITED"
                          />
                        </Stack>
                      )}
                      {row.status === "INACTIVE" && (
                        <Stack
                          direction="row"
                          alignItems="center"
                          spacing={1.25}
                          justifyContent="flex-end"
                        >
                          <Button
                            size="small"
                            color="error"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleActivateMember(row);
                            }}
                          >
                            Activate
                          </Button>
                          <Chip size="small" color="error" label={row.status} />
                        </Stack>
                      )}
                      {row.status === "ACTIVE" && (
                        <Chip size="small" color="success" label={row.status} />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteMember(row);
                        }}
                      >
                        <DeleteOutlined style={{ fontSize: "1.15rem" }} />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Dialog
            open={deleteModalOpen}
            onClose={cancelDeleteMember}
            aria-labelledby="alert-dialog-title"
            aria-describedby="alert-dialog-description"
          >
            <DialogTitle id="alert-dialog-title">Delete Member</DialogTitle>
            <DialogContent>
              <DialogContentText id="alert-dialog-description">
                Are you sure you want to delete this member?
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={cancelDeleteMember} color="error">
                Cancel
              </Button>
              <Button
                onClick={confirmDeleteMember}
                color="primary"
                variant="contained"
                autoFocus
              >
                Confirm
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={activateModalOpen}
            onClose={cancelActivateMember}
            aria-labelledby="alert-dialog-title"
            aria-describedby="alert-dialog-description"
          >
            <DialogTitle id="alert-dialog-title">Activate Member</DialogTitle>
            <DialogContent>
              <DialogContentText id="alert-dialog-description">
                Are you sure you want to activate this member?
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={cancelActivateMember} color="error">
                Cancel
              </Button>
              <Button
                onClick={confirmActivateMember}
                color="primary"
                variant="contained"
                autoFocus
              >
                Confirm
              </Button>
            </DialogActions>
          </Dialog>
        </MainCard>
      </Grid>
    </Grid>
  );
};

export default TabMember;
