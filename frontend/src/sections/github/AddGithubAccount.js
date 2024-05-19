import { useEffect, useState } from "react";
import axios from "axios";
import { Autocomplete } from "@mui/material";

import { CircularProgress } from "@mui/material";

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
  FormControl,
} from "@mui/material";
import AnimateButton from "components/@extended/AnimateButton";

import { useFormik, Form, FormikProvider } from "formik";
import * as Yup from "yup";

// constant
const getInitialValues = (awsAccount) => {
  const newGithubData = {
    name: null,
    path: "",
    branch: "main",
    githubAccountId: "",
  };

  if (awsAccount?.githubData) {
    newGithubData.awsAccount?.githubData;
    return _.merge({}, newGithubData, awsAccount?.githubData);
  }

  return newGithubData;
};

// ==============================|| GitHub Account ADD ||============================== //

const AddGitHubRepo = ({ awsAccount, setAWSAccount, handleNext, state }) => {
  const [installURL, setInstallURL] = useState("");
  const [gitConnected, setGitConnected] = useState(false);
  const [githubRepos, setGithubRepos] = useState([]);
  const [githubAccount, setGithubAccount] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setInstallURL(
      `https://github.com/apps/${process.env.NEXT_PUBLIC_GITHUB_APP_NAME}/installations/new`
    );
  }, []);

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const { data } = await axios.get(`/api/github/get-repositories`);
        const repositories = data.repositories;
        const formattedData = repositories.map((repo) => ({
          id: repo.id,
          name: repo.name,
          owner: repo.owner,
        }));
        setGithubRepos(formattedData);
      } catch (error) {
        console.error(error);
      }
    };

    if (gitConnected) {
      fetchRepos();
    }
  }, [gitConnected]);

  const handleInstall = () => {
    window.open(installURL, "_blank");
  };

  useEffect(() => {
    const checkAppInstalled = async () => {
      try {
        const { data } = await axios.get("/api/github/validate-app-install", {
          params: { state },
        });

        if (data) {
          setGitConnected(true);
          setGithubAccount(data);
        }
      } catch (error) {
        setGitConnected(false);
        console.error(error);
      }
    };

    // Define an async function and call it immediately
    const fetchData = async () => {
      await checkAppInstalled();
      setLoading(false);
    };

    fetchData();

    const interval = setInterval(fetchData, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleRepoChange = async (event, newValue) => {
    try {
      formik.setFieldValue("name", newValue ? newValue : null);

      // const { data } = await axios.get(`/api/github/get-branches`, {
      //   params: {
      //     repoName: newValue?.name,
      //     owner: newValue?.owner?.login,
      //   },
      // });
      // formik.setFieldValue("branch", null);

      // setBranches(data);
    } catch (error) {
      console.error(error);
    }
  };

  const GitHubRepoSchema = Yup.object().shape({
    name: Yup.mixed()
      .nullable()
      .test("isValidName", "Repository name is required", (value) => {
        return (
          value && typeof value.name === "string" && value.name.trim() !== ""
        );
      }),
    // repoPath: Yup.string().matches(
    //   /^([a-zA-Z0-9_.-]+\/)*[a-zA-Z0-9_.-]*\/?$/,
    //   "Invalid repository path"
    // ),
    // branch: Yup.mixed()
    //   .nullable()
    //   .test("isValidBranch", "Branch is required", (value) => {
    //     return value === null || (value && typeof value.name === "string");
    //   }),
  });

  const formik = useFormik({
    initialValues: getInitialValues(awsAccount),

    validationSchema: GitHubRepoSchema,
    onSubmit: async (values, { setSubmitting }) => {
      try {
        values.githubAccountId = githubAccount.id;
        values.login = githubAccount[0].owner.login;
        // var newAWSAccount = awsAccount;
        var newAWSAccount = {
          name: "",
          roleArnEnabled: true,
          roleArn: "",
          sessionDuration: 3600,
          description: "",
        };

        // console.log(githubAccount[0].owner.login);

        newAWSAccount.githubData = values;
        // newAWSAccount.githubData.branch = "main";
        newAWSAccount.workspace = awsAccount?.workspace;
        setAWSAccount(newAWSAccount);
        handleNext();
        setSubmitting(false);
      } catch (error) {
        console.error(error);
        setSubmitting(false);
      }
    },
  });

  const { errors, touched, handleSubmit, isSubmitting, getFieldProps } = formik;

  return (
    <FormikProvider value={formik}>
      <Form autoComplete="off" noValidate onSubmit={handleSubmit}>
        <DialogTitle>Connect to a GitHub Repository</DialogTitle>
        <Divider />
        {loading ? (
          <CircularProgress />
        ) : (
          <DialogContent sx={{ p: 2.5 }}>
            <Grid container spacing={3}>
              {!gitConnected && (
                <Grid item xs={12}>
                  <Button
                    color="primary"
                    variant="contained"
                    onClick={handleInstall}
                  >
                    Install GitHub App
                  </Button>
                </Grid>
              )}
              {gitConnected && (
                <>
                  <Grid item xs={12}>
                    <Stack spacing={1.25}>
                      <InputLabel htmlFor="githubRepo-repository">
                        Repository
                      </InputLabel>
                      <FormControl>
                        <Autocomplete
                          id="githubRepo-name"
                          options={githubRepos}
                          getOptionLabel={(option) =>
                            option ? option.name : null
                          }
                          value={formik.values.name || null}
                          onChange={handleRepoChange}
                          fullWidth
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              placeholder="Select your repository"
                              error={Boolean(touched.name && errors.name)}
                              helperText={touched.name && errors.name}
                            />
                          )}
                        />
                      </FormControl>
                    </Stack>
                  </Grid>
                  {/* <Grid item xs={12}>
                    <Stack spacing={1.25}>
                      <InputLabel htmlFor="githubRepo-branch">
                        Branch
                      </InputLabel>
                      <FormControl fullWidth>
                        <Autocomplete
                          id="githubRepo-branch"
                          options={branches}
                          getOptionLabel={(option) =>
                            option ? option.name : null
                          }
                          value={formik.values.branch || null}
                          onChange={(event, newValue) => {
                            formik.setFieldValue(
                              "branch",
                              newValue ? newValue : null
                            );
                          }}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              placeholder="Select your branch"
                              error={Boolean(touched.branch && errors.branch)}
                              helperText={touched.branch && errors.branch}
                            />
                          )}
                        />
                      </FormControl>
                    </Stack>
                  </Grid> */}
                  {/* <Grid item xs={12}>
                    <Stack spacing={1.25}>
                      <InputLabel htmlFor="githubRepo-repoPath">
                        Repository Path
                      </InputLabel>
                      <TextField
                        fullWidth
                        id="githubRepo-repoPath"
                        placeholder="Path in Repository"
                        {...getFieldProps("repoPath")}
                        error={Boolean(touched.repoPath && errors.repoPath)}
                        helperText={touched.repoPath && errors.repoPath}
                      />
                    </Stack>
                  </Grid> */}
                </>
              )}
            </Grid>
          </DialogContent>
        )}
        <Divider />
        {gitConnected && (
          <DialogActions sx={{ p: 2.5 }}>
            <Grid item xs={12}>
              <Stack direction="row" justifyContent="space-between">
                <AnimateButton>
                  <Button
                    disabled={isSubmitting}
                    variant="contained"
                    type="submit"
                    sx={{ my: 3, ml: 1 }}
                  >
                    Next
                  </Button>
                </AnimateButton>
              </Stack>
            </Grid>
          </DialogActions>
        )}
      </Form>
    </FormikProvider>
  );
};

export default AddGitHubRepo;
