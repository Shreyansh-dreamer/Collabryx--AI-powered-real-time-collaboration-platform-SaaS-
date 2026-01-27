import { Routes, Route } from "react-router-dom";
import NotFound from "./NotFound";
import LandingPage from "./LandingPage/LandingPage";

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage/>}/>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}

export default App;
