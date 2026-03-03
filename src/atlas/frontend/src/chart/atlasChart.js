export function createAtlasChart(containerId, symbol = "EURUSD", interval = "60") {
  if (!window.TradingView) {
    console.error("TradingView no cargó");
    return;
  }

  new window.TradingView.widget({
    autosize: true,
    symbol: symbol,
    interval: interval,
    timezone: "America/Argentina/Buenos_Aires",
    theme: "dark",
    style: "1",
    locale: "es",
    toolbar_bg: "#0f172a",
    enable_publishing: false,
    hide_top_toolbar: false,
    hide_legend: false,
    save_image: false,
    container_id: containerId,
  });
}
