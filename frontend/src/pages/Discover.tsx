import { useNavigate, useSearchParams } from "react-router-dom";
import { Sparkles, SlidersHorizontal } from "lucide-react";
import type { User } from "../types";
import SwipeDiscovery from "../components/SwipeDiscovery";
import Catalog from "../components/Catalog";

export default function Discover({ user }: { user: User }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const catalog = params.get("mode") === "catalog";
  function select(mode: string) {
    const next = new URLSearchParams(params);
    next.set("mode", mode);
    setParams(next, { replace: true });
  }
  return (
    <section className="discovery-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ГОРОД ПОЛОН ВОЗМОЖНОСТЕЙ</div>
          <h1>
            Открывать<span className="brand-dot">.</span>
          </h1>
        </div>
        <button
          className="icon-button"
          aria-label="Изменить интересы"
          onClick={() => navigate("/profile")}
        >
          <SlidersHorizontal size={22} />
        </button>
      </div>
      <button
        className="evening-entry evening-entry-discover"
        onClick={() => navigate("/evening")}
      >
        <Sparkles size={17} />
        <span>Собери мой вечер</span>
        <span aria-hidden="true">→</span>
      </button>
      <div className="segmented discovery-modes" aria-label="Режим поиска">
        <button
          className={!catalog ? "active" : ""}
          aria-pressed={!catalog}
          onClick={() => select("swipes")}
        >
          Свайпы
        </button>
        <button
          className={catalog ? "active" : ""}
          aria-pressed={catalog}
          onClick={() => select("catalog")}
        >
          Каталог
        </button>
      </div>
      {catalog ? <Catalog user={user} /> : <SwipeDiscovery />}
    </section>
  );
}
