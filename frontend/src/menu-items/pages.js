// third-party
import { FormattedMessage } from "react-intl";


// assets
import {
  StockOutlined,
  SettingOutlined,
  PhoneOutlined,
  RocketOutlined,
} from "@ant-design/icons";

import {
  MdWorkspacesOutline,
  MdOutlineIntegrationInstructions,
} from "react-icons/md";

// icons
const icons = { StockOutlined, SettingOutlined, PhoneOutlined, RocketOutlined };

// ==============================|| MENU ITEMS - PAGES ||============================== //

const pages = {
  id: "group-pages",
  type: "group",
  children: [
    {
      id: "aws-account",
      title: <FormattedMessage id="aws account" />,
      type: "item",
      url: "/aws/aws-account-list",
      icon: MdOutlineIntegrationInstructions,
    },
    {
      id: "workspaces",
      title: <FormattedMessage id="workspaces" />,
      type: "item",
      url: "/workspace/workspace-list",
      icon: MdWorkspacesOutline,
    },


  ],
};

export default pages;
