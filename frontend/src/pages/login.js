import PropTypes from "prop-types";

// next
import NextLink from "next/link";
import { getProviders, getCsrfToken } from "next-auth/react";

// material-ui
import { Grid, Link, Stack, Typography } from "@mui/material";
import { useMediaQuery } from "@mui/material";

// project import
import Layout from "layout";
import Page from "components/Page";
import AuthWrapper from "sections/auth/AuthWrapper";
import AuthLogin from "sections/auth/auth-forms/AuthLogin";

// export default function SignIn({ providers, csrfToken }) {
//   const matchDownSM = useMediaQuery((theme) => theme.breakpoints.down("sm"));

//   return (
//     <Page title="Login">
//       <AuthWrapper>
//         <Grid
//           container
//           spacing={3}
//           alignItems="center"
//           justifyContent="center"
//           style={{ minHeight: "100vh" }}
//         >
//           {/* Background Image Side */}
//           <Grid
//             item
//             xs={false}
//             md={7}
//             sx={{
//               backgroundImage: "url(/path-to-your-background-image.jpg)", // replace with your image path
//               backgroundRepeat: "no-repeat",
//               backgroundSize: "cover",
//               backgroundPosition: "center",
//             }}
//           >
//             {/* Image side content if any */}
//           </Grid>

//           {/* Login Button Side */}
//           <Grid
//             item
//             xs={12}
//             md={5}
//             sx={{
//               display: "flex",
//               flexDirection: "column",
//               alignItems: "center",
//               justifyContent: "center",
//             }}
//           >
//             <AuthLogin providers={providers} csrfToken={csrfToken} />
//           </Grid>
//         </Grid>
//       </AuthWrapper>
//     </Page>
//   );
// }

export default function SignIn({ providers, csrfToken }) {
  return (
    <Page title="Login">
      <AuthWrapper>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <AuthLogin providers={providers} csrfToken={csrfToken} />
          </Grid>
        </Grid>
      </AuthWrapper>
    </Page>
  );
}

SignIn.propTypes = {
  providers: PropTypes.object,
  csrfToken: PropTypes.string,
};

SignIn.getLayout = function getLayout(page) {
  return <Layout variant="auth">{page}</Layout>;
};

export async function getServerSideProps(context) {
  const providers = await getProviders();
  const csrfToken = await getCsrfToken(context);

  return {
    props: { providers, csrfToken },
  };
}
