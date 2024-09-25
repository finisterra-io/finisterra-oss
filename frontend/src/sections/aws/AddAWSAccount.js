import PropTypes from "prop-types";
import NextLink from "next/link";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import CircularProgress from "@mui/material/CircularProgress";
import { useDispatch } from "react-redux";
import AnimateButton from "components/@extended/AnimateButton";
import { useRouter } from "next/router";
import {
  Button,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  InputLabel,
  Stack,
  TextField,
  Tooltip,
  Box,
  Autocomplete,
  Typography,
} from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import _ from "lodash";
import * as Yup from "yup";
import { useFormik, Form, FormikProvider } from "formik";
import { openSnackbar } from "store/reducers/snackbar";

const getInitialValues = (awsAccount) => {
  const newAWSAccount = {
    name: "",
    awsRegion: "",
    roleArnEnabled: true,
    roleArn: "",
    region: "",
    sessionDuration: 3600,
    description: "",
  };
  
  if (awsAccount) {
    newAWSAccount.name = awsAccount.name;
    newAWSAccount.roleArnEnabled = awsAccount.roleArnEnabled;
    newAWSAccount.roleArn = awsAccount.roleArn;
    newAWSAccount.region = awsAccount.region;
    newAWSAccount.sessionDuration = awsAccount.sessionDuration;
    newAWSAccount.description = awsAccount.description;
    return _.merge({}, newAWSAccount, awsAccount);
  }
  
  return newAWSAccount;
};

const AddAWSAccount = ({ awsAccount, handleBack }) => {
  const dispatch = useDispatch();
  const [awsAccountId, setAwsAccountId] = useState(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [gitUrlList, setGitUrlList] = useState([]);
  const [workflowUrl, setWorkflowUrl] = useState(null);
  
  const router = useRouter();
  
  const previousRoleArn = useRef("");
  
  const AWSRoleArnRegex = /^arn:aws:iam::\d{12}:role\/[\w+=,.@\-_/]+$/;
  
  const AWSAccountSchema = Yup.object()
  .shape({
    name: Yup.string().max(255).required("Name is required"),
    roleArn: Yup.string().required("Role ARN is required").matches(
      AWSRoleArnRegex,
      "Invalid AWS Role ARN format"
    ),
    awsRegion: Yup.object()
    .required("Region is required")
    .test("isValidBranch", "Invalid region", (value) => {
      return value && typeof value.code === "string";
    }),
    
    sessionDuration: Yup.number()
    .required("Session duration is required")
    .integer("Session duration must be an integer")
    .min(900, "Session duration must be at least 900")
    .max(3600, "Session duration must be at most 3600"),
    description: Yup.string().max(500),
  });
  
  const checkIntervalRef = useRef(null);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  
  const formik = useFormik({
    initialValues: getInitialValues(awsAccount),
    enableReinitialize: true,
    validationSchema: AWSAccountSchema,
    onSubmit: async (values, { setSubmitting }) => {
      try {
        const newAWSAccount = {
          name: values.name,
          roleArnEnabled: values.roleArnEnabled,
          roleArn: values.roleArn,
          region: values.awsRegion.code,
          sessionDuration: parseInt(values.sessionDuration),
          description: values.description,
          tags: [],
          githubData: awsAccount?.githubData,
          workspace: awsAccount?.workspace,
          awsRegion: values.awsRegion,
          awsAccountId: awsAccountId,
        };
        const response = await axios.post("/api/aws/account", newAWSAccount);
        if (awsAccount?.githubData) {
          const newApiKey = {
            name: "Github",
            description: "Github API Key",
          };
          const responseAPI = await axios.post("/api/api-key/api-key", newApiKey);
          const maxRetries = 3;
          let attempts = 0;
          let success = false;
          let responseGit;
          
          while (attempts < maxRetries && !success) {
            try {
              responseGit = await axios.post("/api/github/push-onboarding", {
                gitRepo: { name: newAWSAccount?.githubData?.name.name },
                ftAPIKey: responseAPI.data.createdApiKey,
                awsAccountId: awsAccountId,
                awsRegion: values.awsRegion.code,
              });
              
              success = true; 
            } catch (error) {
              attempts += 1; 
              if (attempts === maxRetries) {
                throw error; 
              }
            }
          }
          
          const generateWorkflow = `generate_tf_code_${awsAccountId}_${values.awsRegion.code}.yaml`;
          
          checkIntervalRef.current = setInterval(async () => {
            try {
              const response = await axios.get(`/api/github/workflow-status`, {
                params: {
                  gitRepoName: newAWSAccount?.githubData?.name.name,
                  workflow: generateWorkflow,
                  head_branch: `finisterra-initial-setup-${awsAccountId}-${values.awsRegion.code}`,
                },
              });
              if (response.data && response.data.status) {
                setWorkflowStatus(response.data.status);
                
                if (response.data.workflowUrl) {
                  setWorkflowUrl(response.data.workflowUrl);
                }
                
                if (response.data.status == "completed") {
                  clearInterval(checkIntervalRef.current);
                }
              }
              
              // Fetch list of PRs
              const prResponse = await axios.get(
                `/api/github/list-pull-requests`,
                {
                  params: {
                    gitRepoName: newAWSAccount?.githubData?.name.name,
                  },
                }
              );
              
              if (prResponse.data && prResponse.data.pullRequests) {
                const newPRs = prResponse.data.pullRequests.filter(
                  (pr) =>
                    pr.title.includes(awsAccountId) &&
                  (pr.title.includes(values.awsRegion.code) ||
                  pr.title.includes("global"))
                );
                
                setGitUrlList([...newPRs]);
              }
            } catch (error) {
              console.error("Error fetching workflow status:", error);
            }
          }, 5000);
        }
        
        dispatch(
          openSnackbar({
            open: true,
            message: "AWS Account successfully created!",
            variant: "alert",
            alert: {
              color: "success",
            },
            close: true,
          })
        );
        const gitUrl = responseGit.data.html_url;
        if (!gitUrlList.includes(gitUrl)) {
          setGitUrlList((prevList) => [gitUrl, ...prevList]);
        }
        setIsSubmitted(true);
        setSubmitting(false);
      } catch (error) {
        console.error(error);
        const errorMessage =
        error.response?.data?.error ?? "Unknown error occurred";
        dispatch(
          openSnackbar({
            open: true,
            message: errorMessage,
            variant: "alert",
            alert: {
              color: "error",
            },
            close: true,
          })
        );
        return false;
      }
    },
  });
  
  useEffect(() => {
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
    };
  }, []);
  
  const regions = [
    { name: "US East (Ohio)", code: "us-east-2" },
    { name: "US East (N. Virginia)", code: "us-east-1" },
    { name: "US West (N. California)", code: "us-west-1" },
    { name: "US West (Oregon)", code: "us-west-2" },
    { name: "Africa (Cape Town)", code: "af-south-1" },
    { name: "Asia Pacific (Hong Kong)", code: "ap-east-1" },
    { name: "Asia Pacific (Hyderabad)", code: "ap-south-2" },
    { name: "Asia Pacific (Jakarta)", code: "ap-southeast-3" },
    { name: "Asia Pacific (Melbourne)", code: "ap-southeast-4" },
    { name: "Asia Pacific (Mumbai)", code: "ap-south-1" },
    { name: "Asia Pacific (Osaka)", code: "ap-northeast-3" },
    { name: "Asia Pacific (Seoul)", code: "ap-northeast-2" },
    { name: "Asia Pacific (Singapore)", code: "ap-southeast-1" },
    { name: "Asia Pacific (Sydney)", code: "ap-southeast-2" },
    { name: "Asia Pacific (Tokyo)", code: "ap-northeast-1" },
    { name: "Canada (Central)", code: "ca-central-1" },
    { name: "Europe (Frankfurt)", code: "eu-central-1" },
    { name: "Europe (Ireland)", code: "eu-west-1" },
    { name: "Europe (London)", code: "eu-west-2" },
    { name: "Europe (Milan)", code: "eu-south-1" },
    { name: "Europe (Paris)", code: "eu-west-3" },
    { name: "Europe (Spain)", code: "eu-south-2" },
    { name: "Europe (Stockholm)", code: "eu-north-1" },
    { name: "Europe (Zurich)", code: "eu-central-2" },
    { name: "Middle East (Bahrain)", code: "me-south-1" },
    { name: "Middle East (UAE)", code: "me-central-1" },
    { name: "South America (São Paulo)", code: "sa-east-1" },
    { name: "AWS GovCloud (US-East)", code: "us-gov-east-1" },
    { name: "AWS GovCloud (US-West)", code: "us-gov-west-1" },
  ];
  
  const handleClose = () => {
    router.push("/aws/aws-account-list");
  };
  
  const handleRoleArnBlur = () => {
    if (formik.values.roleArn !== "") {
      extractAccountIdFromRoleArn(formik.values.roleArn);
      previousRoleArn.current = formik.values.roleArn;
    }
  };
  
  useEffect(() => {
    if (awsAccount?.roleArn) {
      extractAccountIdFromRoleArn(awsAccount?.roleArn);
      previousRoleArn.current = awsAccount.roleArn;
    }
  }, []);
  
  function extractAccountIdFromRoleArn(roleArn) {
    const arnParts = roleArn.split(":");
    if (arnParts.length > 4) {
      setAwsAccountId(arnParts[4]);
    }
  }
  
  const { errors, touched, handleSubmit, isSubmitting, getFieldProps } = formik;
  
  return (
    <>
    {isSubmitted ? (
      // The UI for a successful submission
      <Box sx={{ p: 2.5 }}>
      {gitUrlList &&
        gitUrlList.some((pr) => pr?.url && pr?.url.trim() !== "") && (
          <>
          <Typography>
          Following Pull Requests were created, please review and merge
          them.
          </Typography>
          <ul>
          {gitUrlList
            .filter((pr) => pr.url && pr.url.trim() !== "")
            .sort(
              (a, b) => new Date(a.created_at) - new Date(b.created_at)
            ) // sorting in ascending order
            .map((pr, index) => {
              const displayTitle = pr.title.startsWith("Automatic PR")
              ? pr.title.split(" ")[3].split("-")[0]
              : pr.title;
              
              return (
                <li key={index}>
                <a
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#305bdd",
                  textDecoration: "none",
                }}
                >
                {displayTitle.toUpperCase()}
                </a>
                </li>
              );
            })}
            </ul>
            </>
          )}
          
          <Box display="flex" alignItems="center" mt={2}>
          {workflowStatus !== "completed" && (
            <CircularProgress size={24} sx={{ mr: 1 }} />
          )}
          {workflowUrl ? (
            <Typography>
            <a
            href={workflowUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "#305bdd",
              textDecoration: "none",
            }}
            >
            {workflowStatus !== "completed"
              ? "Generating Code..."
              : `Code generation ${workflowStatus}`}
              </a>
              </Typography>
            ) : (
              <Typography>
              {workflowStatus !== "completed"
                ? "Generating Code..."
                : `Code generation ${workflowStatus}`}
                </Typography>
              )}
              </Box>
              
              <Box mt={4}>
              <Button variant="contained" onClick={handleClose}>
              Close
              </Button>
              </Box>
              </Box>
            ) : (
              <FormikProvider value={formik}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
              <Form autoComplete="off" noValidate onSubmit={handleSubmit}>
              <DialogTitle>Connect AWS with Github</DialogTitle>
              <Divider />
              <DialogContent sx={{ p: 2.5 }}>
              <Grid item xs={12}>
              <Grid container spacing={3}>
              <Grid item xs={12}>
              <Stack spacing={1.25}>
              <InputLabel htmlFor="awsAccount-name">
              Account Name
              </InputLabel>
              <TextField
              fullWidth
              id="awsAccount-name"
              placeholder="Name"
              {...getFieldProps("name")}
              error={Boolean(touched.name && errors.name)}
              helperText={touched.name && errors.name}
              />
              </Stack>
              </Grid>
              
              <Grid item xs={12}>
              <Stack spacing={1.25}>
              <InputLabel htmlFor="awsAccount-region">
              Region
              </InputLabel>
              
              <Autocomplete
              id="awsAccount-awsRegion"
              options={regions}
              required
              getOptionLabel={(option) =>
                option ? option.name : null
              }
              value={formik.values.awsRegion || null}
              onChange={(event, newValue) => {
                formik.setFieldValue(
                  "awsRegion",
                  newValue ? newValue : null
                );
              }}
              renderInput={(params) => (
                <TextField
                placeholder="Region"
                {...params}
                error={Boolean(
                  touched.awsRegion && errors.awsRegion
                )}
                helperText={
                  formik.touched.awsRegion
                  ? formik.errors.awsRegion
                  : ""
                }
                required
                />
              )}
              />
              </Stack>
              </Grid>
              
              <Grid item xs={12}>
              <Stack spacing={1.25}>
              <InputLabel htmlFor="awsAccount-roleArn">
              Role ARN
              </InputLabel>
              <Box
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              >
              <TextField
              fullWidth
              id="awsAccount-roleArn"
              placeholder="Role ARN"
              {...getFieldProps("roleArn")}
              onBlur={handleRoleArnBlur}
              error={Boolean(touched.roleArn && errors.roleArn)}
              helperText={touched.roleArn && errors.roleArn}
              style={{ flex: 1, marginRight: 8 }} // give it a flex of 1 to take up available space
              />
              <NextLink
              href={`https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://s3.amazonaws.com/finisterra-aws-connect/ft-ro-gha-cicd-role.yaml&stackName=ft-ro-gha-cicd-role&param_GitRepositoryOwner=${awsAccount.githubData.login}`}
              >
              <a target="_blank" rel="noopener noreferrer">
              <Tooltip title="Click to Create Role on AWS">
              <Button
              aria-label="create role"
              color="secondary"
              variant="contained"
              >
              Create Role
              </Button>
              </Tooltip>
              </a>
              </NextLink>
              </Box>
              </Stack>
              </Grid>
              </Grid>
              </Grid>
              </DialogContent>
              <Divider />
              <DialogActions sx={{ p: 2.5 }}>
              <Grid
              container
              justifyContent="space-between"
              alignItems="center"
              >
              <Grid item></Grid>
              <Grid item>
              <Stack direction="row" spacing={2} alignItems="center">
              <Button
              onClick={handleBack}
              sx={{ my: 3, ml: 1 }}
              disabled={isSubmitting}
              >
              Back
              </Button>
              
              <AnimateButton>
              <Button
              type="submit"
              variant="contained"
              disabled={isSubmitting}
              >
              {isSubmitting ? (
                <CircularProgress size={24} />
              ) : awsAccount?.id ? (
                "Update"
              ) : (
                "Create"
              )}
              </Button>
              </AnimateButton>
              </Stack>
              </Grid>
              </Grid>
              </DialogActions>
              </Form>
              </LocalizationProvider>
              </FormikProvider>
            )}
            </>
          );
        };
        
        AddAWSAccount.propTypes = {
          awsAccount: PropTypes.object,
          setAWSAccount: PropTypes.func,
          handleNext: PropTypes.func,
        };
        
        export default AddAWSAccount;
        