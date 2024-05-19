import React from "react";
import { useFormik } from "formik";
import * as Yup from "yup";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import SendIcon from "@mui/icons-material/Send";

const validationSchema = Yup.object({
  inviteEmail: Yup.string()
    .email("Invalid email address")
    .required("Invitation email is required"),
});

export default function SendInvitation({ onSend }) {
  const formik = useFormik({
    initialValues: {
      inviteEmail: "",
    },
    validationSchema,
    onSubmit: async (values, { resetForm }) => {
      // Handle invitation sending
      await onSend(values.inviteEmail);
      resetForm();
    },
  });

  return (
    <Box
      component="form"
      onSubmit={formik.handleSubmit}
      sx={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        maxWidth: "400px",
        margin: "0 auto",
      }}
      noValidate
    >
      <Typography variant="h4" mb={2}>
        Send Invitation
      </Typography>
      <TextField
        name="inviteEmail"
        label="Invite Email"
        value={formik.values.inviteEmail}
        onChange={formik.handleChange}
        error={formik.touched.inviteEmail && Boolean(formik.errors.inviteEmail)}
        helperText={formik.touched.inviteEmail && formik.errors.inviteEmail}
        margin="normal"
        fullWidth
      />
      <Button
        variant="contained"
        color="primary"
        type="submit"
        endIcon={<SendIcon />}
        sx={{ mt: 2 }}
      >
        Send Invite
      </Button>
    </Box>
  );
}
