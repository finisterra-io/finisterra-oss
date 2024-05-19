import { Button, Grid, InputLabel, Stack, TextField } from "@mui/material";
import { useFormik } from "formik";
import * as Yup from "yup";
import { useState, useEffect } from "react";
import debounce from "lodash.debounce";
import { useSession, signOut } from "next-auth/react";

import { useRouter } from "next/router";

import MainCard from "components/MainCard";

import { useDispatch } from "react-redux";
import { openSnackbar } from "store/reducers/snackbar";

const TabOrganization = () => {
  const router = useRouter();
  const dispatch = useDispatch();
  const [nameAvailable, setNameAvailable] = useState(true);
  const [organizationName, setOrganizationName] = useState("");
  const [initialOrganizationName, setInitialOrganizationName] = useState("");
  const { data: session } = useSession();
  const organizationId = session?.organizationId;

  useEffect(() => {
    const fetchOrganizationDetails = async () => {
      if (!session.organizationId) return;
      const response = await fetch(
        "/api/organization/crud?organizationId=" + organizationId
      );
      const data = await response.json();
      setOrganizationName(data.name);
      setInitialOrganizationName(data.name);
      formik.setFieldValue("organizationName", data.name);
    };

    fetchOrganizationDetails();
  }, [session]);

  const formik = useFormik({
    initialValues: {
      organizationName: "",
    },
    validationSchema: Yup.object({
      organizationName: Yup.string()
        .matches(/^[A-Za-z0-9]*$/, "Only alphanumeric characters are allowed")
        .max(50, "Must be 50 characters or less")
        .required("Required")
        .test("is-unique", "Name not available", async (value, testContext) => {
          if (!value) return true;
          if (value === initialOrganizationName) {
            setNameAvailable(true);
            return true;
          }
          const alphanumeric = /^[A-Za-z0-9]*$/;
          const isValid = alphanumeric.test(value);
          const isWithinLength = value.length <= 50;
          if (!isValid || !isWithinLength) return false;

          const response = await fetch(
            `/api/organization/check-name?orgName=${value}`
          );
          const data = await response.json();
          setNameAvailable(!data.exists || value === initialOrganizationName);
          return !data.exists || value === initialOrganizationName;
        }),
    }),
    onSubmit: async (values) => {
      if (!nameAvailable) return;

      try {
        const response = await fetch("/api/organization/crud", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            organizationName: values.organizationName,
            organizationId,
          }),
        });
        const data = await response.json();
        setOrganizationName(data.name);
        dispatch(
          openSnackbar({
            open: true,
            message: "Organization updated successfully.",
            variant: "alert",
            alert: {
              color: "success",
            },
            close: true,
          })
        );
        if (!organizationId) {
          router.push("/");
        }
      } catch (error) {
        dispatch(
          openSnackbar({
            open: true,
            message: "Error updating organization.",
            variant: "alert",
            alert: {
              color: "error",
            },
            close: true,
          })
        );
      }
    },
  });

  useEffect(() => {
    const checkNameAvailability = async () => {
      const response = await fetch(
        `/api/organization/check-name?orgName=${formik.values.organizationName}`
      );
      const data = await response.json();
      if (formik.values.organizationName === initialOrganizationName) {
        setNameAvailable(true);
        return true;
      }
      setNameAvailable(!data.exists);
    };
    const debouncedCheckNameAvailability = debounce(checkNameAvailability, 100);
    if (formik.values.organizationName) {
      debouncedCheckNameAvailability();
    }
  }, [formik.values.organizationName]);

  return (
    <form onSubmit={formik.handleSubmit}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <MainCard title="General Settings">
            <Grid container spacing={3}>
              <Grid item xs={12} sm={12}>
                <Stack spacing={1.25}>
                  <InputLabel htmlFor="organization-name">
                    Organization Name
                  </InputLabel>
                  <TextField
                    fullWidth
                    id="organization-name"
                    name="organizationName"
                    placeholder="Organization Name"
                    autoFocus
                    value={formik.values.organizationName}
                    onChange={formik.handleChange}
                    onBlur={formik.handleBlur}
                    error={
                      formik.touched.organizationName &&
                      Boolean(formik.errors.organizationName)
                    }
                    helperText={
                      formik.touched.organizationName &&
                      formik.errors.organizationName
                    }
                  />
                </Stack>
              </Grid>
            </Grid>
          </MainCard>
        </Grid>
        <Grid item xs={12}>
          <Stack
            direction="row"
            justifyContent="flex-end"
            alignItems="center"
            spacing={2}
          >
            {!session.organizationId && (
              <Button
                variant="outlined"
                color="error"
                onClick={() => signOut()}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              variant="contained"
              disabled={
                !formik.isValid || formik.isSubmitting || !nameAvailable
              }
            >
              {session.organizationId ? "Update" : "Create"} Organization
            </Button>
          </Stack>
        </Grid>
      </Grid>
    </form>
  );
};

export default TabOrganization;
