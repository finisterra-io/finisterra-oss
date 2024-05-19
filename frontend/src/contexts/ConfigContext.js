import PropTypes from "prop-types";
import { createContext } from "react";

// project import
import defaultConfig from "config";
import useLocalStorage from "hooks/useLocalStorage";

// initial state
const initialState = {
  ...defaultConfig,
  onChangeContainer: () => {},
  onChangeLocalization: () => {},
  onChangeMode: () => {},
  onChangePresetColor: () => {},
  onChangeDirection: () => {},
  onChangeMiniDrawer: () => {},
  onChangeMenuOrientation: () => {},
  onChangeFontFamily: () => {},
};

// ==============================|| CONFIG CONTEXT & PROVIDER ||============================== //

const ConfigContext = createContext(initialState);

function ConfigProvider({ children }) {
  const [config, setConfig] = useLocalStorage(
    "finisterra-config",
    initialState
  );

  const onChangeContainer = () => {
    setConfig({
      ...config,
      container: !config.container,
    });
  };

  const onChangeLocalization = (lang) => {
    setConfig({
      ...config,
      i18n: lang,
    });
  };

  const onChangeMode = (mode) => {
    if (mode === "dark") {
      mode = "light";
    } else {
      mode = "dark";
    }
    setConfig({
      ...config,
      mode,
    });
  };

  const onChangePresetColor = (theme) => {
    setConfig({
      ...config,
      presetColor: theme,
    });
  };

  const onChangeDirection = (direction) => {
    setConfig({
      ...config,
      themeDirection: direction,
    });
  };

  const onChangeMiniDrawer = (miniDrawer) => {
    setConfig({
      ...config,
      miniDrawer,
    });
  };

  const onChangeMenuOrientation = (layout) => {
    setConfig({
      ...config,
      menuOrientation: layout,
    });
  };

  const onChangeFontFamily = (fontFamily) => {
    setConfig({
      ...config,
      fontFamily,
    });
  };

  return (
    <ConfigContext.Provider
      value={{
        ...config,
        onChangeContainer,
        onChangeMode,
        onChangeLocalization,
        onChangePresetColor,
        onChangeDirection,
        onChangeMiniDrawer,
        onChangeMenuOrientation,
        onChangeFontFamily,
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
}

ConfigProvider.propTypes = {
  children: PropTypes.node,
};

export { ConfigProvider, ConfigContext };
