import PropTypes from "prop-types";

import { useState, useEffect } from "react";

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
  CircularProgress,
  IconButton,
} from "@mui/material";
import { AiOutlineCheckCircle } from "react-icons/ai";
import { VscError } from "react-icons/vsc";

// project import
import MainCard from "components/MainCard";

// ==============================|| AWS ACCOUNT - CARD PREVIEW ||============================== //

export default function AddAWSAccountProgress({ awsAccount, saveStatus }) {
  const matchDownMD = useMediaQuery((theme) => theme.breakpoints.down("md"));

  return (
    <>
      <Box id="PopupPrint" sx={{ px: { xs: 2, sm: 3, md: 5 }, py: 1 }}>
        <DialogContent dividers sx={{ px: 0 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={12} xl={12}>
              <Grid container spacing={2.25}>
                <Grid item xs={12}>
                  <MainCard title="Progress ">
                    <List sx={{ py: 0 }}>
                      {/* <ListItem divider>
                        <Grid container spacing={matchDownMD ? 0.5 : 3}>
                          <Grid item xs={12} md={12}>
                            <Stack spacing={0.5}>
                              <Typography color="secondary">
                                DB Configuration
                              </Typography>
                            </Stack>
                          </Grid>
                        </Grid>
                      </ListItem> */}
                      {/* <ListItem divider>
                        <Grid container alignItems="center">
                          <Grid item>
                            {saveStatus.dbCreated == "success" && (
                              <IconButton size="1.5rem" color="success">
                                <AiOutlineCheckCircle />
                              </IconButton>
                            )}
                            {saveStatus.dbCreated == "processing" && (
                              <CircularProgress size="1.5rem" color="info" />
                            )}
                            {saveStatus.dbCreated == "error" && (
                              <VscError size="1.5rem" color="red" />
                            )}
                          </Grid>
                          <Grid item>
                            <Box ml={1}>
                              <Typography>Database Configuration</Typography>
                            </Box>
                          </Grid>
                        </Grid>
                      </ListItem> */}

                      {/* <ListItem divider>
                        <Grid container spacing={matchDownMD ? 0.5 : 3}>
                          <Grid item xs={12} md={12}>
                            <Stack spacing={0.5}>
                              <Typography color="secondary">
                                State S3 Bucket
                              </Typography>
                            </Stack>
                          </Grid>
                        </Grid>
                      </ListItem>
                      <ListItem divider>
                        <Grid container alignItems="center">
                          <Grid item>
                            {saveStatus.s3BucketCreated == "success" && (
                              <IconButton size="1.5rem" color="success">
                                <AiOutlineCheckCircle />
                              </IconButton>
                            )}
                            {saveStatus.s3BucketCreated == "processing" && (
                              <CircularProgress size="1.5rem" color="info" />
                            )}
                            {saveStatus.s3BucketCreated == "error" && (
                              <VscError size="1.5rem" color="red" />
                            )}
                          </Grid>
                          <Grid item>
                            <Box ml={1}>
                              <Typography>
                                {awsAccount?.workspace?.state?.s3Bucket}
                              </Typography>
                            </Box>
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
                            </Stack>
                          </Grid>
                        </Grid>
                      </ListItem>

                      <ListItem divider>
                        <Grid container alignItems="center">
                          <Grid item>
                            {saveStatus.dynamodDBCreated == "success" && (
                              <IconButton size="1.5rem" color="success">
                                <AiOutlineCheckCircle />
                              </IconButton>
                            )}
                            {saveStatus.dynamodDBCreated == "processing" && (
                              <CircularProgress size="1.5rem" color="info" />
                            )}
                            {saveStatus.dynamodDBCreated == "error" && (
                              <VscError size="1.5rem" color="red" />
                            )}
                          </Grid>

                          <Grid item>
                            <Box ml={1}>
                              <Typography>
                                {awsAccount?.workspace?.state?.dynamoDBTable}
                              </Typography>
                            </Box>
                          </Grid>
                        </Grid>
                      </ListItem> */}
                      {/* <ListItem divider>
                        <Grid container spacing={matchDownMD ? 0.5 : 3}>
                          <Grid item xs={12} md={12}>
                            <Stack spacing={0.5}>
                              <Typography color="secondary">
                                Workspaces
                              </Typography>
                            </Stack>
                          </Grid>
                        </Grid>
                      </ListItem> */}

                      {/* {awsAccount?.finalWorkspace?.map((workspace) => (
                        <ListItem key={workspace.id}>
                          <Grid container alignItems="center">
                            <Grid item>
                              {saveStatus.workspacesCreated[workspace.id]
                                ?.status == "success" && (
                                <IconButton size="1.5rem" color="success">
                                  <AiOutlineCheckCircle />
                                </IconButton>
                              )}
                              {saveStatus.workspacesCreated[workspace.id]
                                ?.status == "processing" && (
                                <CircularProgress size="1.5rem" color="info" />
                              )}
                              {saveStatus.workspacesCreated[workspace.id]
                                ?.status == "error" && (
                                <VscError size="1.5rem" color="red" />
                              )}
                            </Grid>
                            <Grid item>
                              <Box ml={1}>
                                <Typography>{workspace.name}</Typography>
                              </Box>
                            </Grid>
                          </Grid>
                        </ListItem>
                      ))} */}
                    </List>
                  </MainCard>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </DialogContent>
      </Box>
    </>
  );
}

AddAWSAccountProgress.propTypes = {
  awsAccount: PropTypes.object,
};
