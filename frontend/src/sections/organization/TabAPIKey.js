import { useState, useEffect } from "react";
import { useSelector, dispatch } from "store";
import { getApiKeys, deleteApiKey, createApiKey } from "store/reducers/apiKey";
import { openSnackbar } from "store/reducers/snackbar";
import { Formik, Form, Field, ErrorMessage } from "formik";

import {
  Button,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  TextField,
  InputLabel,
  MenuItem,
} from "@mui/material";
import IconButton from "components/@extended/IconButton";

import { CopyOutlined } from "@ant-design/icons";

import MainCard from "components/MainCard";
import { DeleteOutlined } from "@ant-design/icons";

import * as Yup from "yup";

const TabAPIKey = () => {
  const { apiKeys } = useSelector((state) => state.apiKey);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedAPIKey, setSelectedAPIKey] = useState(null);

  const handleCopyToClipboard = (key) => {
    navigator.clipboard.writeText(key).then(
      () => {
        console.log("Text successfully copied");
        // Optionally show some notification that the copy was successful.
      },
      (err) => {
        console.error("Unable to copy text: ", err);
        // Handle the error, perhaps show a notification to the user.
      }
    );
  };

  useEffect(() => {
    dispatch(getApiKeys());
  }, []);

  const handleDeleteAPIKey = (keyId) => {
    setSelectedAPIKey(keyId);
    setDeleteModalOpen(true);
  };

  const confirmDeleteAPIKey = async () => {
    dispatch(deleteApiKey(selectedAPIKey));
    setDeleteModalOpen(false);
  };

  const cancelDeleteAPIKey = () => {
    setSelectedAPIKey(null);
    setDeleteModalOpen(false);
  };

  const validationSchema = Yup.object().shape({
    name: Yup.string()
      .matches(/^[a-zA-Z0-9]*$/, "Only alphanumeric characters are allowed.")
      .max(55, "Name should not exceed 55 characters.")
      .required("Name is required"),
  });

  const handleSend = async (values, { resetForm }) => {
    values.description = values.name;
    dispatch(createApiKey(values));
    resetForm();
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <MainCard title="API Keys" content={false}>
          <Stack spacing={2.5} sx={{ p: 2.5 }}>
            <Formik
              initialValues={{ name: "" }}
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
                        htmlFor="outlined-name"
                        sx={{ paddingTop: "0.2rem" }}
                      >
                        Name
                      </InputLabel>
                      <Field
                        as={TextField}
                        fullWidth
                        id="outlined-name"
                        name="name"
                        variant="outlined"
                        placeholder="Enter a name"
                      />
                      <div style={{ height: "1.2rem" }}>
                        <ErrorMessage name="name">
                          {(msg) => (
                            <Typography variant="caption" color="error">
                              {msg}
                            </Typography>
                          )}
                        </ErrorMessage>
                      </div>
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
                      Create
                    </Button>
                  </Stack>
                </Form>
              )}
            </Formik>
          </Stack>

          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ pl: 3 }}>Name</TableCell>
                <TableCell sx={{ pl: 3 }}>API Key</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {apiKeys.map((key) => (
                <TableRow hover key={key.id}>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">{key.name}</Typography>
                  </TableCell>
                  <TableCell sx={{ pl: 3 }} component="th">
                    <Typography variant="subtitle1">
                      {"****************************************" +
                        (key.key ? key.key.slice(40) : "")}

                      <IconButton
                        size="small"
                        color="secondary"
                        onClick={() => handleCopyToClipboard(key.key)}
                        title="Copy to Clipboard"
                      >
                        <CopyOutlined style={{ fontSize: "1.15rem" }} />
                      </IconButton>
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      color="secondary"
                      onClick={() => handleDeleteAPIKey(key.id)}
                    >
                      <DeleteOutlined style={{ fontSize: "1.15rem" }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Dialog
            open={deleteModalOpen}
            onClose={cancelDeleteAPIKey}
            aria-labelledby="alert-dialog-title"
            aria-describedby="alert-dialog-description"
          >
            <DialogTitle id="alert-dialog-title">Delete API Key</DialogTitle>
            <DialogContent>
              <DialogContentText id="alert-dialog-description">
                Are you sure you want to delete this API key?
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={cancelDeleteAPIKey} color="error">
                Cancel
              </Button>
              <Button
                onClick={confirmDeleteAPIKey}
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

export default TabAPIKey;
