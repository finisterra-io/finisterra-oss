import PropTypes from "prop-types";
import { useState } from "react";
// material-ui
import {
  Box,
  Chip,
  Dialog,
  Divider,
  Fade,
  Grid,
  List,
  ListItem,
  ListItemText,
  Menu,
  MenuItem,
  Typography,
} from "@mui/material";

// project import
import AWSAccountPreview from "sections/aws-account/AWSAccountPreview";
import AlertAWSAccountDelete from "sections/aws-account/AlertAWSAccountDelete";
import AddAWSAccount from "sections/aws-account/AddAWSAccount";
import MainCard from "components/MainCard";
import IconButton from "components/@extended/IconButton";
import { PopupTransition } from "components/@extended/Transitions";

import { useDispatch } from "react-redux";

import { deleteAWSAccount } from "store/reducers/aws-account";

// assets
import { MoreOutlined } from "@ant-design/icons";

// ==============================|| AWS ACCOUNT - CARD ||============================== //

const AWSAccountCard = ({ awsAccount }) => {
  const dispatch = useDispatch();

  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };
  const handleClose = () => {
    setOpen(false);
  };

  const [openAlert, setOpenAlert] = useState(false);

  const handleAlertClose = () => {
    setOpenAlert(!openAlert);
    handleMenuClose();
  };

  const handleAlertDelete = () => {
    dispatch(deleteAWSAccount(awsAccount.id));
    handleAlertClose();
  };

  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);
  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const [add, setAdd] = useState(false);
  const handleAdd = () => {
    setAdd(!add);
  };

  return (
    <>
      <MainCard
        sx={{
          height: 1,
          "& .MuiCardContent-root": {
            height: 1,
            display: "flex",
            flexDirection: "column",
          },
        }}
      >
        <Grid id="print" container spacing={2.25}>
          <Grid item xs={12}>
            <List sx={{ width: 1, p: 0 }}>
              <ListItem
                disablePadding
                secondaryAction={
                  <IconButton
                    edge="end"
                    aria-label="comments"
                    color="secondary"
                    onClick={handleMenuClick}
                  >
                    <MoreOutlined style={{ fontSize: "1.15rem" }} />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={
                    <Typography variant="h3">{awsAccount.name}</Typography>
                  }
                />
              </ListItem>
            </List>
            <Menu
              id="fade-menu"
              MenuListProps={{
                "aria-labelledby": "fade-button",
              }}
              anchorEl={anchorEl}
              open={openMenu}
              onClose={handleMenuClose}
              TransitionComponent={Fade}
              anchorOrigin={{
                vertical: "bottom",
                horizontal: "right",
              }}
              transformOrigin={{
                vertical: "top",
                horizontal: "right",
              }}
            >
              <MenuItem onClick={handleAdd}>Edit</MenuItem>
              <MenuItem onClick={handleAlertClose}>Delete</MenuItem>
            </Menu>
          </Grid>
          <Grid item xs={12}>
            <Divider />
          </Grid>

          <Grid item xs={12}>
            <Grid container spacing={1}>
              <Grid item xs={12}>
                <List
                  sx={{
                    p: 0,
                    overflow: "hidden",
                    "& .MuiListItem-root": { px: 0, py: 0.5 },
                  }}
                >
                  <ListItem>
                    <ListItemText
                      primary={<Typography variant="h5">Role ARN</Typography>}
                      secondary={<Typography>{awsAccount.roleArn}</Typography>}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary={
                        <Typography variant="h5">Session Duration</Typography>
                      }
                      secondary={
                        <Typography color="secondary">
                          {awsAccount.sessionDuration}
                        </Typography>
                      }
                    />
                  </ListItem>
                </List>
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12}>
            <Typography color="secondary">{awsAccount.description}</Typography>
          </Grid>
          <Grid item xs={12}>
            <Box>
              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  listStyle: "none",
                  p: 0.5,
                  m: 0,
                }}
                component="ul"
              >
                {awsAccount.tags.map((tag, index) => (
                  <ListItem
                    disablePadding
                    key={index}
                    sx={{ width: "auto", pr: 0.75, pb: 0.75 }}
                  >
                    <Chip
                      color="secondary"
                      variant="outlined"
                      size="small"
                      label={tag}
                    />
                  </ListItem>
                ))}
              </Box>
            </Box>
          </Grid>
        </Grid>
      </MainCard>

      {/* edit awsAccount dialog */}
      <Dialog
        maxWidth="sm"
        fullWidth
        TransitionComponent={PopupTransition}
        onClose={handleAdd}
        open={add}
        sx={{ "& .MuiDialog-paper": { p: 0 } }}
      >
        <AddAWSAccount awsAccount={awsAccount} onCancel={handleAdd} />
      </Dialog>
      <AWSAccountPreview
        awsAccount={awsAccount}
        open={open}
        onClose={handleClose}
      />
      <AlertAWSAccountDelete
        title={awsAccount.name}
        open={openAlert}
        handleClose={handleAlertClose}
        handleDelete={handleAlertDelete}
      />
    </>
  );
};

AWSAccountCard.propTypes = {
  awsAccount: PropTypes.object,
};

export default AWSAccountCard;
