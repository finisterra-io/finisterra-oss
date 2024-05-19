import PropTypes from "prop-types";

// material-ui
import {
  useMediaQuery,
  Box,
  DialogContent,
  Grid,
  List,
  ListItem,
  Stack,
  Typography,
} from "@mui/material";

import AddAWSAccountProgress from "sections/aws/AddAWSAccountProgress";

// project import
import MainCard from "components/MainCard";
import SimpleBar from "components/third-party/SimpleBar";

// ==============================|| AWS ACCOUNT - CARD PREVIEW ||============================== //

export default function AWSAccountPreview({ awsAccount, saveStatus }) {
  const matchDownMD = useMediaQuery((theme) => theme.breakpoints.down("md"));

  return (
    <>
      {saveStatus?.submitting ? (
        <AddAWSAccountProgress
          awsAccount={awsAccount}
          saveStatus={saveStatus}
        />
      ) : (
        <Box id="PopupPrint" sx={{ px: { xs: 2, sm: 3, md: 5 }, py: 1 }}>
          <DialogContent dividers sx={{ px: 0 }}>
            {/* <SimpleBar sx={{ height: "calc(100vh - 290px)" }}> */}
            <Grid container spacing={3}>
              <Grid item xs={12} sm={12} xl={12}>
                <Grid container spacing={2.25}>
                  <Grid item xs={12}>
                    <MainCard title="AWS Information">
                      <List sx={{ py: 0 }}>
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Account Name
                                </Typography>
                                <Typography>{awsAccount?.name}</Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>

                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Role ARN
                                </Typography>
                                <Typography>{awsAccount?.roleArn}</Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>
                        {/* <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Session Duration
                                </Typography>
                                <Typography>
                                  {awsAccount?.sessionDuration}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem> */}
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Description
                                </Typography>
                                <Typography>
                                  {awsAccount?.description}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>
                      </List>
                    </MainCard>
                  </Grid>

                  <Grid item xs={12}>
                    <MainCard title="Workspaces">
                      <List sx={{ py: 0 }}>
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Region
                                </Typography>
                                <Typography>
                                  {awsAccount?.workspace?.awsRegion?.name}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>

                        {/* <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  State S3 Bucket
                                </Typography>
                                <Typography>
                                  {awsAccount?.workspace?.state?.s3Bucket}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  State Lock Dynamodb Table
                                </Typography>
                                <Typography>
                                  {awsAccount?.workspace?.state?.dynamoDBTable}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem> */}
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Workspaces
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>

                        {awsAccount?.workspace?.activeGroups.map((group) => (
                          <ListItem key={group.id}>
                            <Grid container>
                              <Grid item xs={12}>
                                <Typography
                                  sx={{
                                    "::before": {
                                      content: '"• "',
                                      color: "text.secondary",
                                      fontWeight: "bold",
                                    },
                                  }}
                                >
                                  {group.name}
                                </Typography>
                              </Grid>
                            </Grid>
                          </ListItem>
                        ))}
                      </List>
                    </MainCard>
                  </Grid>

                  <Grid item xs={12}>
                    <MainCard title="Git Repository Information">
                      <List sx={{ py: 0 }}>
                        <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Repository Name
                                </Typography>
                                <Typography>
                                  {awsAccount?.githubData?.name.name}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem>
                        {/* <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">
                                  Branch
                                </Typography>
                                <Typography>
                                  {awsAccount?.githubData?.branch.name}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem> */}
                        {/* <ListItem divider>
                          <Grid container spacing={matchDownMD ? 0.5 : 3}>
                            <Grid item xs={12} md={12}>
                              <Stack spacing={0.5}>
                                <Typography color="secondary">Path</Typography>
                                <Typography>
                                  {awsAccount?.githubData?.path}
                                </Typography>
                              </Stack>
                            </Grid>
                          </Grid>
                        </ListItem> */}
                      </List>
                    </MainCard>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
            {/* </SimpleBar> */}
          </DialogContent>
        </Box>
      )}
    </>
  );
}

AWSAccountPreview.propTypes = {
  awsAccount: PropTypes.object,
};
