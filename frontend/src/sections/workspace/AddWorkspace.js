import PropTypes from "prop-types";

import { useState, useEffect, useRef } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import { useDispatch } from "react-redux";
import {
  Button,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  InputLabel,
  TextField,
  Typography,
  Checkbox,
  FormControlLabel,
} from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import * as Yup from "yup";
import { useFormik, Form, FormikProvider } from "formik";
import { createWorkspace, updateWorkspace } from "store/reducers/workspace";

const getInitialValues = async (workspaceId) => {
  const newWorkspace = {
    name: "",
    scanInterval: 3600,
    description: "",
    awsRegion: "",
    enabled: true,
  };

  if (workspaceId) {
    try {
      const res = await fetch(`/api/workspace/${workspaceId}`);
      if (!res.ok) {
        throw new Error(res.status);
      }
      const workspace = await res.json();

      // Ensure all values are not null
      Object.keys(workspace).forEach((key) => {
        if (workspace[key] === null) {
          workspace[key] = "";
        }
      });

      return _.merge({}, newWorkspace, workspace);
    } catch (error) {
      console.error("Failed to fetch workspace:", error);
      return newWorkspace;
    }
  }
  return newWorkspace;
};

const AddWorkspace = ({ workspaceId }) => {
  const dispatch = useDispatch();
  const [workspace, setWorkspace] = useState(null);
  const [displayStateKey, setDisplayStateKey] = useState("");
  const [displayModule, setDisplayModule] = useState("");

  const [initialWorkspaceValues, setInitialWorkspaceValues] = useState({
    name: "",
    scanInterval: 3600,
    description: "",
    awsRegion: "",
    enabled: true,
  });

  useEffect(() => {
    const fetchInitialValues = async () => {
      const initialValues = await getInitialValues(workspaceId);
      setInitialWorkspaceValues(initialValues);
      setDisplayModule(`${initialValues.providerGroup.name}`);
      setWorkspace(initialValues);
    };

    fetchInitialValues();
  }, [workspaceId]);

  const WorkspaceSchema = Yup.object().shape({
    name: Yup.string().max(255).required("Name is required"),
    scanInterval: Yup.number()
      .required("Scan interval is required")
      .integer("Scan interval must be an integer")
      .min(900, "Scan interval must be at least 900")
      .max(8640000, "Scan interval must be at most 8640000"),
    awsRegion: Yup.string().max(255).required("AWS Region is required"),
    description: Yup.string().max(500),
    enabled: Yup.boolean(),
  });

  const formik = useFormik({
    initialValues: initialWorkspaceValues,
    enableReinitialize: true,
    validationSchema: WorkspaceSchema,
    onSubmit: async (values, { setSubmitting }) => {
      try {
        const newWorkspace = {
          name: values.name,
          scanInterval: parseInt(values.scanInterval),
          description: values.description,
          awsRegion: values.awsRegion,
          organizationId: workspace?.organizationId,
          awsAccountId: workspace?.awsAccountId,
          providerGroupId: workspace?.providerGroupId,
          enabled: values.enabled,
        };
        if (workspace?.id) {
          newWorkspace.id = workspace.id;
          await dispatch(updateWorkspace(newWorkspace));
        } else {
          await dispatch(createWorkspace(newWorkspace));
          setWorkspace(newWorkspace);
        }
        setSubmitting(false);
      } catch (error) {
        console.error(error);
      }
    },
  });

  const { errors, touched, handleSubmit, isSubmitting, getFieldProps } = formik;

  return (
    <>
      <FormikProvider value={formik}>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Form autoComplete="off" noValidate onSubmit={handleSubmit}>
            <DialogTitle>Workspace Details</DialogTitle>
            <Divider />
            <DialogContent sx={{ p: 2.5 }}>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <InputLabel>Name</InputLabel>
                  <Typography>{formik.values.name}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <InputLabel>Provider</InputLabel>
                  <Typography>AWS</Typography>
                </Grid>
                <Grid item xs={12}>
                  <InputLabel>AWS Region</InputLabel>
                  <Typography>{formik.values.awsRegion}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <InputLabel>Module</InputLabel>
                  <Typography>{displayModule}</Typography>
                </Grid>
                {/* <Grid item xs={12}>
                  <InputLabel>State Key</InputLabel>
                  <Typography>{displayStateKey}</Typography>
                </Grid> */}
                {/* <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Scan Interval (seconds)"
                    {...getFieldProps("scanInterval")}
                    error={Boolean(touched.scanInterval && errors.scanInterval)}
                    helperText={touched.scanInterval && errors.scanInterval}
                    type="number"
                  />
                </Grid> */}
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formik.values.enabled || false}
                        {...getFieldProps("enabled")}
                      />
                    }
                    label="Enabled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    {...getFieldProps("description")}
                    error={Boolean(touched.description && errors.description)}
                    helperText={touched.description && errors.description}
                    multiline
                  />
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button
                variant="contained"
                color="primary"
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting && <CircularProgress size={20} color="inherit" />}
                {workspaceId ? "Update" : "Create"}
              </Button>
            </DialogActions>
          </Form>
        </LocalizationProvider>
      </FormikProvider>
    </>
  );
};

AddWorkspace.propTypes = {
  workspaceId: PropTypes.string,
};

export default AddWorkspace;
