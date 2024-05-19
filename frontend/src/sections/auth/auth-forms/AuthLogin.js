import PropTypes from "prop-types";
import React from "react";

// next
import Image from "next/image";
import NextLink from "next/link";
import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/router";
import { useEffect } from "react";

// material-ui

import {
  Box,
  useMediaQuery,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  FormHelperText,
  Grid,
  Link,
  InputAdornment,
  InputLabel,
  OutlinedInput,
  Stack,
  Typography,
} from "@mui/material";

// third party
import * as Yup from "yup";
import { Formik } from "formik";

// project import
import { APP_DEFAULT_PATH } from "config";
import IconButton from "components/@extended/IconButton";
import AnimateButton from "components/@extended/AnimateButton";

// assets
import { EyeOutlined, EyeInvisibleOutlined } from "@ant-design/icons";

const Auth0 = "/assets/images/icons/auth0.svg";
const Cognito = "/assets/images/icons/aws-cognito.svg";
const Google = "/assets/images/icons/google.svg";
const Github = "/assets/images/icons/github.svg";

// ============================|| AWS CONNITO - LOGIN ||============================ //

const AuthLogin = ({ providers, csrfToken }) => {
  const matchDownSM = useMediaQuery((theme) => theme.breakpoints.down("sm"));
  const [checked, setChecked] = React.useState(false);
  const [capsWarning, setCapsWarning] = React.useState(false);

  const { data: session } = useSession();

  const [showPassword, setShowPassword] = React.useState(false);
  const handleClickShowPassword = () => {
    setShowPassword(!showPassword);
  };

  const handleMouseDownPassword = (event) => {
    event.preventDefault();
  };

  const onKeyDown = (keyEvent) => {
    if (keyEvent.getModifierState("CapsLock")) {
      setCapsWarning(true);
    } else {
      setCapsWarning(false);
    }
  };

  const router = useRouter();
  const { from } = router.query;
  const redirectTo = from ? decodeURIComponent(from) : APP_DEFAULT_PATH;
  console.log("redirectTo", redirectTo);

  return (
    <>
      <Divider sx={{ mt: 2 }}>
        <Typography variant="h4"> Login with</Typography>
      </Divider>
      {providers && (
        <Stack
          direction="row"
          spacing={matchDownSM ? 1 : 2}
          justifyContent={matchDownSM ? "space-around" : "space-between"}
          sx={{
            mt: 3,
            "& .MuiButton-startIcon": {
              mr: matchDownSM ? 0 : 1,
              ml: matchDownSM ? 0 : -0.5,
            },
          }}
        >
          {Object.values(providers).map((provider) => {
            if (provider.id === "login" || provider.id === "register") {
              return;
            }
            return (
              <Box key={provider.name} sx={{ width: "100%" }}>
                {provider.id === "google" && (
                  <Button
                    variant="outlined"
                    color="secondary"
                    fullWidth={!matchDownSM}
                    startIcon={
                      <Image
                        src={Google}
                        alt="Twitter"
                        width={16}
                        height={16}
                      />
                    }
                    onClick={() =>
                      signIn(provider.id, { callbackUrl: redirectTo })
                    }
                  >
                    {!matchDownSM && "Google"}
                  </Button>
                )}
                {provider.id === "github" && (
                  <Button
                    variant="outlined"
                    color="secondary"
                    fullWidth={!matchDownSM}
                    startIcon={
                      <Image
                        src={Github}
                        alt="Twitter"
                        width={16}
                        height={16}
                      />
                    }
                    onClick={() =>
                      signIn(provider.id, { callbackUrl: redirectTo })
                    }
                  >
                    {!matchDownSM && "Github"}
                  </Button>
                )}
                {/* {provider.id === "auth0" && (
                  <Button
                    variant="outlined"
                    color="secondary"
                    fullWidth={!matchDownSM}
                    startIcon={
                      <Image src={Auth0} alt="Twitter" width={16} height={16} />
                    }
                    onClick={() =>
                      signIn(provider.id, { callbackUrl: redirectTo })
                    }
                  >
                    {!matchDownSM && "Auth0"}
                  </Button>
                )}
                {provider.id === "cognito" && (
                  <Button
                    variant="outlined"
                    color="secondary"
                    fullWidth={!matchDownSM}
                    startIcon={
                      <Image
                        src={Cognito}
                        alt="Twitter"
                        width={16}
                        height={16}
                      />
                    }
                    onClick={() =>
                      signIn(provider.id, { callbackUrl: redirectTo })
                    }
                  >
                    {!matchDownSM && "Cognito"}
                  </Button>
                )} */}
              </Box>
            );
          })}
        </Stack>
      )}
      {!providers && (
        <Box sx={{ mt: 3 }}>
          <FirebaseSocial />
        </Box>
      )}
    </>
  );
};

AuthLogin.propTypes = {
  providers: PropTypes.object,
  csrfToken: PropTypes.string,
};

export default AuthLogin;
