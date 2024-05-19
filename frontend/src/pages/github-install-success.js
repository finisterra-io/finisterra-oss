import AuthWrapper from "sections/auth/AuthWrapper";
import { useRouter } from "next/router";

import {
  Button,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

import AnimateButton from "components/@extended/AnimateButton";

import { useEffect, useState } from "react";

// project import
import Layout from "layout";
import Page from "components/Page";

export default function GithubInstallSuccess() {
  const [installed, setInstalled] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const fetchGithubAppStatus = async () => {
      const installation_id = router.query.installation_id;

      if (installation_id) {
        const response = await fetch(
          `/api/github/app-callback?installation_id=${installation_id}`
        );
        if (response.status === 200) {
          setInstalled(true);
        }
      }
    };
    fetchGithubAppStatus();
  }, [router.query]); // Added router.query to the dependency array of useEffect

  return (
    <Page title="Onboard">
      <AuthWrapper>
        {installed ? (
          <Grid container spacing={3}>
            <DialogTitle>GitHub App Installed</DialogTitle>
            <Divider />

            <DialogContent sx={{ p: 2.5 }}>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Typography variant="body">
                    The GitHub App has been installed successfully. You can now
                    close this window and return to the application.
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Stack spacing={1.25}></Stack>
                </Grid>
              </Grid>
            </DialogContent>
            <Divider />
            <DialogActions sx={{ p: 2.5 }}>
              <Grid item xs={12}>
                <Stack direction="row" justifyContent="space-between">
                  <AnimateButton>
                    <Button
                      variant="contained"
                      sx={{ my: 3, ml: 1 }}
                      onClick={() => window.close()}
                    >
                      Close
                    </Button>
                  </AnimateButton>
                </Stack>
              </Grid>
            </DialogActions>
          </Grid>
        ) : (
          <Typography variant="body">Validating Installation...</Typography>
        )}
      </AuthWrapper>
    </Page>
  );
}

GithubInstallSuccess.getLayout = function getLayout(page) {
  return <Layout variant="onboard">{page}</Layout>;
};
