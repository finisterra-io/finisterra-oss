import { useState, useEffect } from "react";

import React from "react";
import { useFormik } from "formik";
import * as Yup from "yup";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";

import { Grid, Stack, Typography, Alert } from "@mui/material";
import { useRouter } from "next/router";

import axios from "axios";
import { useDebounce } from "use-debounce";

import { useSession } from "next-auth/react";

const validationSchema = Yup.object({
  orgName: Yup.string().required("Organization name is required"),
});

export default function CreateOrganization({ onCreate }) {
  const router = useRouter();
  const [error, setError] = useState(null);

  const formik = useFormik({
    initialValues: {
      orgName: "",
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        setError(null);
        const response = await axios.post("/api/organization/create", {
          orgName: values.orgName,
        });
        if (response.data.success) {
          localStorage.setItem("organizationId", response.data.organization.id);
          router.push("/");
        } else {
          setError(response.data.error);
        }
      } catch (error) {
        console.log(error);
        setError("Failed to create organization");
      }
    },
  });

  const [orgNameExists, setOrgNameExists] = useState(false);
  const [debouncedOrgName] = useDebounce(formik.values.orgName, 100); // Debounce orgName by 500ms

  useEffect(() => {
    if (debouncedOrgName.trim() !== "") {
      checkOrganizationName(debouncedOrgName);
    }
  }, [debouncedOrgName]);

  const checkOrganizationName = async (name) => {
    try {
      const response = await axios.get("/api/organization/check-name", {
        params: { orgName: name },
      });

      setOrgNameExists(response.data.exists);
    } catch (error) {
      console.error("Error checking organization name:", error);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
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
          <TextField
            name="orgName"
            placeholder="Organization Name"
            type="text"
            value={formik.values.orgName}
            onChange={formik.handleChange}
            error={formik.touched.orgName && Boolean(formik.errors.orgName)}
            helperText={formik.touched.orgName && formik.errors.orgName}
            fullWidth
          />
          {orgNameExists && (
            <Alert severity="error" style={{ marginTop: "1rem" }}>
              Organization name already exists. Please choose another one.
            </Alert>
          )}
          {error && (
            <Alert severity="error" style={{ marginTop: "1rem" }}>
              {error}
            </Alert>
          )}
          <Button
            variant="contained"
            color="primary"
            type="submit"
            sx={{ mt: 2 }}
            disabled={orgNameExists || formik.values.orgName.trim() === ""}
          >
            Create
          </Button>
        </Box>
      </Grid>
    </Grid>
  );
}
