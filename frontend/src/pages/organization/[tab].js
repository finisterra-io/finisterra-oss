import { useState } from "react";

// next
import { useRouter } from "next/router";

// material-ui
import { Box, Tab, Tabs } from "@mui/material";

// project import
import Layout from "layout";
import Page from "components/Page";
import MainCard from "components/MainCard";
import TabOrganization from "sections/organization/TabOrganization";
import TabMember from "sections/organization/TabMember";
import TabAPIKey from "sections/organization/TabAPIKey";
import TabBilling from "sections/organization/TabBilling";


// assets
import {
  ContainerOutlined,
  TeamOutlined,
  LockOutlined,
  CreditCardOutlined,
} from "@ant-design/icons";

// ==============================|| PROFILE - ACCOUNT ||============================== //

const AccountProfile = () => {
  const router = useRouter();
  const { tab } = router.query;

  const [value, setValue] = useState(tab);

  const handleChange = (event, newValue) => {
    setValue(newValue);
    router.push(`/organization/${newValue}`);
  };

  return (
    <Page title="Account Profile">
      <MainCard border={false} boxShadow>
        <Box sx={{ borderBottom: 1, borderColor: "divider", width: "100%" }}>
          <Tabs
            value={value}
            onChange={handleChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="account profile tab"
          >
            <Tab
              label="Organization"
              icon={<ContainerOutlined />}
              value="details"
              iconPosition="start"
            />
            <Tab
              label="Members"
              icon={<TeamOutlined />}
              value="members"
              iconPosition="start"
            />
            <Tab
              label="Api Keys"
              icon={<LockOutlined />}
              value="apikeys"
              iconPosition="start"
            />
            <Tab
              label="Billing"
              icon={<CreditCardOutlined />}
              value="billing"
              iconPosition="start"
            />
          </Tabs>
        </Box>
        <Box sx={{ mt: 2.5 }}>
          {tab === "details" && <TabOrganization />}
          {tab === "members" && <TabMember />}
          {tab === "apikeys" && <TabAPIKey />}
          {tab === "billing" && <TabBilling />}
        </Box>
      </MainCard>
    </Page>
  );
};

AccountProfile.getLayout = function getLayout(page) {
  return <Layout>{page}</Layout>;
};

export default AccountProfile;
