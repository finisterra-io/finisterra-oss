import PropTypes from "prop-types";
import { useState } from "react";

// material-ui
import {
  Button,
  Dialog,
  DialogContent,
  Stack,
  Typography,
  TextField,
} from "@mui/material";

// project import
import Avatar from "components/@extended/Avatar";
import { PopupTransition } from "components/@extended/Transitions";

// assets
import { DeleteFilled } from "@ant-design/icons";

// ==============================|| AWS ACCOUNT - DELETE ||============================== //

export default function AlertAWSAccountDelete({
  title,
  open,
  handleClose,
  handleDelete,
}) {
  const [inputValue, setInputValue] = useState("");

  const handleInputChange = (event) => {
    setInputValue(event.target.value);
  };
  return (
    <Dialog
      open={open}
      onClose={() => handleClose(false)}
      keepMounted
      TransitionComponent={PopupTransition}
      maxWidth="xs"
      aria-labelledby="column-delete-title"
      aria-describedby="column-delete-description"
    >
      <DialogContent sx={{ mt: 2, my: 1 }}>
        <Stack alignItems="center" spacing={3.5}>
          <Avatar
            color="error"
            sx={{ width: 72, height: 72, fontSize: "1.75rem" }}
          >
            <DeleteFilled />
          </Avatar>
          <Stack spacing={2}>
            <Typography variant="h4" align="center">
              Are you sure you want to delete?
            </Typography>
            <Typography align="center">
              By deleting
              <Typography variant="subtitle1" component="span">
                {" "}
                &quot;{title}&quot;{" "}
              </Typography>
              account, you will not be able to connect to it again.
            </Typography>
            <TextField
              fullWidth
              placeholder={`Type ${title} to confirm`}
              value={inputValue}
              onChange={handleInputChange}
              variant="outlined"
            />
          </Stack>

          <Stack direction="row" spacing={2} sx={{ width: 1 }}>
            <Button
              fullWidth
              onClick={() => handleClose(false)}
              color="secondary"
              variant="outlined"
            >
              Cancel
            </Button>
            <Button
              fullWidth
              color="error"
              variant="contained"
              onClick={() => {
                setInputValue("");
                handleDelete(true);
              }}
              autoFocus
              disabled={inputValue !== title}
            >
              Delete
            </Button>
          </Stack>
        </Stack>
      </DialogContent>
    </Dialog>
  );
}

AlertAWSAccountDelete.propTypes = {
  title: PropTypes.string,
  open: PropTypes.bool,
  handleClose: PropTypes.func,
  handleDelete: PropTypes.func,
};
