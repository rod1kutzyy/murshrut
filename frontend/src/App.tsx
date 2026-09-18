import { useEffect, useState } from "react";
import {
  Routes,
  Route,
  Navigate,
  NavLink,
  useNavigate,
  useLocation,
} from "react-router-dom";
import {
  MapPin,
  ChevronRight,
  Heart,
  Compass,
  Map as MapIcon,
  SlidersHorizontal,
} from "lucide-react";
import { api, setToken } from "./api";
import type { Config, User } from "./types";
import { Mascot } from "./components/Mascot";
import { State } from "./components/State";
import PreferencesPage from "./pages/PreferencesPage";
import MyEvents from "./pages/MyEvents";
import Discover from "./pages/Discover";
import EventDetails from "./pages/EventDetails";
import MapPage from "./pages/MapPage";
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    let cancelled = false;
    setError("");
    (async () => {
      const cfg = await api<Config>("/config");
      const initData =
        window.WebApp?.initData ||
        new URLSearchParams(window.location.hash.slice(1)).get("WebAppData");
      if (!initData && !cfg.demo_mode)
        throw new Error("Откройте это мини-приложение внутри MAX.");
      const auth = await api<{ user: User; access_token: string }>(
        initData ? "/auth/max" : "/auth/demo",
        {
          method: "POST",
          body: initData ? JSON.stringify({ init_data: initData }) : undefined,
        },
      );
      if (cancelled) return;
      setToken(auth.access_token);
      setUser(auth.user);
      setConfig(cfg);
      const start =
        window.WebApp?.initDataUnsafe?.start_param ||
        new URLSearchParams(window.location.search).get("startapp");
      if (start?.startsWith("event_"))
        navigate(`/events/${encodeURIComponent(start.slice(6))}`, {
          replace: true,
        });
    })().catch((e) => {
      if (!cancelled) setError(e.message);
    });
    return () => {
      cancelled = true;
    };
  }, [attempt, navigate]);
  useEffect(() => {
    const back = window.WebApp?.BackButton;
    if (!back) return;
    const callback = () => navigate(-1);
    if (
      location.pathname.startsWith("/events/") ||
      location.pathname === "/profile"
    )
      back.show();
    else back.hide();
    back.onClick(callback);
    return () => back.offClick(callback);
  }, [location.pathname, navigate]);
  if (error)
    return (
      <State
        title="Не удалось открыть приложение"
        text={error}
        action={() => setAttempt((v) => v + 1)}
      />
    );
  if (!user || !config)
    return (
      <State
        title="Мур ищет ваш маршрут…"
        text="Ещё мгновение — и начнём"
        loading
      />
    );
  if (!user.onboarding_completed)
    return <PreferencesPage config={config} onSaved={setUser} onboarding />;
  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink to="/" className="brand">
          <Mascot size={38} />
          <span>
            муршрут<span className="brand-dot">.</span>
          </span>
        </NavLink>
        <NavLink to="/profile" className="city-link">
          <MapPin size={14} />
          {user.city}
          <ChevronRight size={14} />
        </NavLink>
      </header>
      {config.event_provider === "demo" && (
        <div className="demo-label">ДЕМО · вымышленные мероприятия</div>
      )}
      <main>
        <Routes>
          <Route path="/" element={<MyEvents />} />
          <Route path="/discover" element={<Discover user={user} />} />
          <Route
            path="/events/:id"
            element={<EventDetails config={config} />}
          />
          <Route path="/map" element={<MapPage />} />
          <Route
            path="/profile"
            element={<PreferencesPage config={config} onSaved={setUser} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <nav className="bottom-nav" aria-label="Основная навигация">
        <NavLink to="/" end>
          <Heart size={21} />
          <span>Мои события</span>
        </NavLink>
        <NavLink to="/discover">
          <Compass size={21} />
          <span>Открывать</span>
        </NavLink>
        <NavLink to="/map">
          <MapIcon size={21} />
          <span>Карта</span>
        </NavLink>
        <NavLink to="/profile">
          <SlidersHorizontal size={21} />
          <span>Мой вкус</span>
        </NavLink>
      </nav>
    </div>
  );
}
