import { useDispatch } from 'react-redux';
import { useRouter } from 'next/router';
import { Button, FormHelperText, Grid, InputLabel, OutlinedInput, Stack, Typography } from '@mui/material';
import { Formik } from 'formik';
import * as Yup from 'yup';
import { openSnackbar } from 'store/reducers/snackbar';
import AnimateButton from 'components/@extended/AnimateButton';

const AuthForgotPassword = () => {
  const dispatch = useDispatch();
  const router = useRouter();

  return (
    <Formik
      initialValues={{
        email: '',
        submit: null
      }}
      validationSchema={Yup.object().shape({
        email: Yup.string().email('Must be a valid email').max(255).required('Email is required')
      })}
      onSubmit={async (values, { setErrors, setStatus, setSubmitting }) => {
        try {
          const response = await fetch('/api/auth/reset-password', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: values.email }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.message || 'Something went wrong');
          }

          setStatus({ success: true });
          setSubmitting(false);
          dispatch(
            openSnackbar({
              open: true,
              message: 'Check mail for reset password link',
              variant: 'alert',
              alert: {
                color: 'success'
              },
              close: false
            })
          );
          setTimeout(() => {
            router.push('/check-mail');
          }, 1500);
        } catch (err) {
          setStatus({ success: false });
          setErrors({ submit: err.message });
          setSubmitting(false);
        }
      }}
    >
      {({ errors, handleBlur, handleChange, handleSubmit, isSubmitting, touched, values }) => (
        <form noValidate onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Stack spacing={1}>
                <InputLabel htmlFor="email-forgot">Email Address</InputLabel>
                <OutlinedInput
                  fullWidth
                  error={Boolean(touched.email && errors.email)}
                  id="email-forgot"
                  type="email"
                  value={values.email}
                  name="email"
                  onBlur={handleBlur}
                  onChange={handleChange}
                  placeholder="Enter email address"
                  inputProps={{}}
                />
                {touched.email && errors.email && (
                  <FormHelperText error id="helper-text-email-forgot">
                    {errors.email}
                  </FormHelperText>
                )}
              </Stack>
            </Grid>
            {errors.submit && (
              <Grid item xs={12}>
                <FormHelperText error>{errors.submit}</FormHelperText>
              </Grid>
            )}
            <Grid item xs={12} sx={{ mb: -2 }}>
              <Typography variant="caption">Do not forget to check SPAM box.</Typography>
            </Grid>
            <Grid item xs={12}>
              <AnimateButton>
                <Button disableElevation disabled={isSubmitting} fullWidth size="large" type="submit" variant="contained" color="primary">
                  Send Password Reset Email
                </Button>
              </AnimateButton>
            </Grid>
          </Grid>
        </form>
      )}
    </Formik>
  );
};

export default AuthForgotPassword;
