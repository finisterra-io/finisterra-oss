import PropTypes from "prop-types";
import { useState, useEffect } from "react";

import { BsMoon, BsSun } from "react-icons/bs";
import { CiSettings } from "react-icons/ci";
import { getSession } from "next-auth/react";

import useConfig from "hooks/useConfig";

import NextLink from "next/link";
// material-ui
import {
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from "@mui/material";

// assets
import { LogoutOutlined, UserOutlined } from "@ant-design/icons";

// ==============================|| HEADER PROFILE - PROFILE TAB ||============================== //

const ProfileTab = ({ handleLogout }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const handleListOrganizationClick = (event, index) => {
    setSelectedIndex(index);
  };

  const [session, setSession] = useState(null);

  useEffect(() => {
    const fetchSession = async () => {
      const session = await getSession();
      setSession(session);
    };
    fetchSession();
  }, []);

  const { mode, onChangeMode } = useConfig();

  const handleModeChange = (mode) => {
    onChangeMode(mode);
  };

  return (
    <List
      component="nav"
      sx={{ p: 0, "& .MuiListItemIcon-root": { minWidth: 32 } }}
    >
      <NextLink href="/organization/details" passHref>
        <ListItemButton
          selected={selectedIndex === 0}
          onClick={(event) => handleListOrganizationClick(event, 0)}
        >
          <ListItemIcon>
            <CiSettings />
          </ListItemIcon>
          <ListItemText
            primary="Settings"
            // primary={
            //   session?.organizationName === "setmeup"
            //     ? "Organization"
            //     : session?.organizationName
            //         ?.split(" ")
            //         .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            //         .join(" ") || "Organization"
            // }
          />
        </ListItemButton>
      </NextLink>
      {/* <ListItemButton
        selected={selectedIndex === 0}
        onClick={(event) => handleListItemClick(event, 0)}
      >
        <ListItemIcon>
          <CiSettings />
        </ListItemIcon>
        <ListItemText primary="Organization" />
      </ListItemButton> */}
      {/* </NextLink> */}

      {/* <ListItemButton
        selected={selectedIndex === 3}
        onClick={(event) => handleListItemClick(event, 3)}
      >
        <ListItemIcon>
          <ProfileOutlined />
        </ListItemIcon>
        <ListItemText primary="Social Profile" />
      </ListItemButton>
      <ListItemButton
        selected={selectedIndex === 4}
        onClick={(event) => handleListItemClick(event, 4)}
      >
        <ListItemIcon>
          <WalletOutlined />
        </ListItemIcon>
        <ListItemText primary="Billing" />
      </ListItemButton> */}

      <ListItemButton
        selected={selectedIndex === 1}
        onClick={() => handleModeChange(mode)}
      >
        <ListItemIcon>{mode == "light" ? <BsMoon /> : <BsSun />}</ListItemIcon>
        <ListItemText primary={mode == "light" ? "Dark Mode" : "Light Mode"} />
      </ListItemButton>
      <ListItemButton selected={selectedIndex === 3} onClick={handleLogout}>
        <ListItemIcon>
          <LogoutOutlined />
        </ListItemIcon>
        <ListItemText primary="Logout" />
      </ListItemButton>
    </List>
  );
};

ProfileTab.propTypes = {
  handleLogout: PropTypes.func,
};

export default ProfileTab;
