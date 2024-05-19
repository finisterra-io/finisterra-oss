import PropTypes from "prop-types";
import { useState, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import { useDispatch } from "react-redux";
import {
  Button,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  TextField,
  FormControlLabel,
  Checkbox,
  Switch,
} from "@mui/material";
import * as Yup from "yup";
import { useFormik, Form, FormikProvider } from "formik";
import { createAWSAccount, updateAWSAccount } from "store/reducers/aws-account";

const getInitialValues = async (awsAccountId) => {
  const newAwsAccount = {
    name: "",
    roleArn: "",
    sessionDuration: 3600,
    description: "",
  };

  if (awsAccountId) {
    try {
      const res = await fetch(`/api/aws/${awsAccountId}`);
      if (!res.ok) {
        throw new Error(res.status);
      }
      const awsAccount = await res.json();

      // Ensure all values are not null
      Object.keys(awsAccount).forEach((key) => {
        if (awsAccount[key] === null) {
          awsAccount[key] = "";
        }
      });

      return { ...newAwsAccount, ...awsAccount };
    } catch (error) {
      console.error("Failed to fetch AWS account:", error);
      return newAwsAccount;
    }
  }
  return newAwsAccount;
};

const AddAwsAccount = ({ awsAccountId }) => {
  const dispatch = useDispatch();

  const [initialAwsAccountValues, setInitialAwsAccountValues] = useState({
    name: "",
    roleArn: "",
    sessionDuration: 3600,
    description: "",
  });

  useEffect(() => {
    const fetchInitialValues = async () => {
      const initialValues = await getInitialValues(awsAccountId);
      setInitialAwsAccountValues(initialValues);
    };

    fetchInitialValues();
  }, [awsAccountId]);

  const AWSRoleArnRegex = /^arn:aws:iam::\d{12}:role\/[\w+=,.@\-_/]+$/;

  const AwsAccountSchema = Yup.object().shape({
    name: Yup.string().max(255).required("Name is required"),
    // roleArn: Yup.string()
    //   .matches(AWSRoleArnRegex, "Invalid AWS Role ARN format")
    //   .required("Role ARN is required"),
    sessionDuration: Yup.number()
      .required("Session duration is required")
      .integer("Session duration must be an integer")
      .min(900, "Session duration must be at least 900")
      .max(3600, "Session duration must be at most 3600"),
    description: Yup.string().max(500),
  });

  const formik = useFormik({
    initialValues: initialAwsAccountValues,
    enableReinitialize: true,
    validationSchema: AwsAccountSchema,
    onSubmit: async (values, { setSubmitting }) => {
      try {
        const newAwsAccount = {
          id: values.id,
          githubData: null,
          workspace: null,
          awsRegion: null,
          awsAccountId: initialAwsAccountValues.awsAccountId,
          name: values.name,
          roleArn: values.roleArn,
          sessionDuration: values.sessionDuration,
          description: values.description,
          enabled: values.enabled,
          tags: [],
        };
        if (awsAccountId) {
          await dispatch(updateAWSAccount(newAwsAccount));
        } else {
          await dispatch(createAWSAccount(newAwsAccount));
        }
        setSubmitting(false);
      } catch (error) {
        console.error(error);
      }
    },
  });

  const { errors, touched, handleSubmit, isSubmitting, getFieldProps } = formik;

  return (
    <FormikProvider value={formik}>
      <Form autoComplete="off" noValidate onSubmit={handleSubmit}>
        <DialogTitle>AWS Account Details</DialogTitle>
        <Divider />
        <DialogContent sx={{ p: 2.5 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                id="awsAccount-name"
                label="Name"
                {...getFieldProps("name")}
                error={Boolean(touched.name && errors.name)}
                helperText={touched.name && errors.name}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                id="awsAccount-roleArn"
                label="Role ARN"
                {...getFieldProps("roleArn")}
                error={Boolean(touched.roleArn && errors.roleArn)}
                helperText={touched.roleArn && errors.roleArn}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formik.values.enabled || false}
                    {...getFieldProps("enabled")}
                    color="primary"
                  />
                }
                label="Enabled"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                id="awsAccount-description"
                multiline
                rows={2}
                label="Description"
                {...getFieldProps("description")}
                error={Boolean(touched.description && errors.description)}
                helperText={touched.description && errors.description}
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
            {awsAccountId ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Form>
    </FormikProvider>
  );
};

AddAwsAccount.propTypes = {
  awsAccountId: PropTypes.string,
};

export default AddAwsAccount;
