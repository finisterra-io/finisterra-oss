// third-party
import { combineReducers } from "redux";

// project import
import menu from "./menu";
import snackbar from "./snackbar";
import awsAccount from "./aws-account";
import workspace from "./workspace";
import member from "./member";
import apiKey from "./apiKey";
import usage from "./usage";

// ==============================|| COMBINE REDUCERS ||============================== //

const reducers = combineReducers({
  menu,
  snackbar,
  awsAccount,
  workspace,
  member,
  apiKey,
  usage,
});

export default reducers;
