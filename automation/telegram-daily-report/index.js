const DEFAULT_CITY = process.env.CITY || "Istanbul";
const DEFAULT_LAT = Number(process.env.LAT || 41.0082);
const DEFAULT_LON = Number(process.env.LON || 28.9784);
const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const FAVORITE_TEAMS = [
  "Galatasaray",
  "Fenerbahce",
  "Besiktas",
  "Trabzonspor",
  "Real Madrid",
  "Barcelona",
  "Manchester City",
  "Liverpool",
  "Bayern Munich",
  "PSG",
  "Juventus",
  "Inter",
  "Milan",
  "Arsenal",
  "Chelsea"
];

function ensureEnv() {
  if (!TELEGRAM_TOKEN || !TELEGRAM_CHAT_ID) {
    throw new Error(
      "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variable."
    );
  }
}

function formatPrice(value) {
  if (!Number.isFinite(value)) return "N/A";
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

function getWeatherEmoji(code) {
  if ([0].includes(code)) return "☀️";
  if ([1, 2].includes(code)) return "🌤️";
  if ([3].includes(code)) return "☁️";
  if ([45, 48].includes(code)) return "🌫️";
  if ([51, 53, 55, 56, 57].includes(code)) return "🌦️";
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return "🌧️";
  if ([71, 73, 75, 77, 85, 86].includes(code)) return "❄️";
  if ([95, 96, 99].includes(code)) return "⛈️";
  return "🌍";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText} (${url})`);
  }
  return response.json();
}

async function getWeather() {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", DEFAULT_LAT);
  url.searchParams.set("longitude", DEFAULT_LON);
  url.searchParams.set("current", "temperature_2m,weather_code,wind_speed_10m");
  url.searchParams.set("timezone", "Europe/Istanbul");

  const data = await fetchJson(url.toString());
  const current = data.current || {};

  return {
    city: DEFAULT_CITY,
    temperature: current.temperature_2m,
    windSpeed: current.wind_speed_10m,
    code: current.weather_code
  };
}

async function getAssetPrice(symbol) {
  const url = `https://stooq.com/q/l/?s=${encodeURIComponent(symbol)}&f=sd2t2ohlcv&h&e=json`;
  const data = await fetchJson(url);
  const quote = data?.symbols?.[0];
  if (!quote || !quote.close || quote.close === "N/D") {
    return null;
  }
  return Number(quote.close);
}

async function getMarkets() {
  const [gold, silver, bitcoin, ethereum] = await Promise.all([
    getAssetPrice("xauusd"),
    getAssetPrice("xagusd"),
    getAssetPrice("btcusd"),
    getAssetPrice("ethusd")
  ]);

  return { gold, silver, bitcoin, ethereum };
}

function normalizeTeamName(name = "") {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function matchScore(homeTeam, awayTeam) {
  const homeNormalized = normalizeTeamName(homeTeam);
  const awayNormalized = normalizeTeamName(awayTeam);

  return FAVORITE_TEAMS.reduce((score, team) => {
    const favorite = normalizeTeamName(team);
    const add = homeNormalized.includes(favorite) || awayNormalized.includes(favorite) ? 1 : 0;
    return score + add;
  }, 0);
}

async function getLeagueMatches(leagueCode) {
  const url = `https://site.api.espn.com/apis/site/v2/sports/soccer/${leagueCode}/scoreboard`;
  const data = await fetchJson(url);
  const events = data?.events || [];

  return events.map((event) => {
    const competition = event.competitions?.[0];
    const home = competition?.competitors?.find((team) => team.homeAway === "home");
    const away = competition?.competitors?.find((team) => team.homeAway === "away");

    return {
      league: data?.league?.name || leagueCode,
      startDate: event.date,
      status: competition?.status?.type?.shortDetail || "",
      homeTeam: home?.team?.displayName || "",
      awayTeam: away?.team?.displayName || "",
      score: matchScore(home?.team?.displayName || "", away?.team?.displayName || "")
    };
  });
}

async function getFavoriteMatches() {
  const leagues = ["tur.1", "eng.1", "esp.1", "uefa.champions"];
  const allMatches = (await Promise.all(leagues.map(getLeagueMatches))).flat();

  return allMatches
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return new Date(a.startDate) - new Date(b.startDate);
    })
    .slice(0, 5);
}

function formatTelegramMessage(weather, markets, matches) {
  const weatherEmoji = getWeatherEmoji(weather.code);

  const matchText = matches.length
    ? matches
        .map((match, index) => {
          const localTime = new Date(match.startDate).toLocaleTimeString("tr-TR", {
            timeZone: "Europe/Istanbul",
            hour: "2-digit",
            minute: "2-digit"
          });
          return `${index + 1}) ${match.homeTeam} - ${match.awayTeam} (${match.league}, ${localTime})`;
        })
        .join("\n")
    : "Bugün öne çıkan maç bulunamadı.";

  return [
    `Günaydın! ☕`,
    "",
    `📅 ${new Date().toLocaleDateString("tr-TR", { timeZone: "Europe/Istanbul" })}`,
    `🌤️ Hava Durumu (${weather.city}): ${weatherEmoji} ${weather.temperature ?? "N/A"}°C, Rüzgar ${weather.windSpeed ?? "N/A"} km/s`,
    "",
    "💰 Piyasa Özeti:",
    `• Altın (XAU/USD): ${formatPrice(markets.gold)}`,
    `• Gümüş (XAG/USD): ${formatPrice(markets.silver)}`,
    `• Bitcoin (BTC/USD): ${formatPrice(markets.bitcoin)}`,
    `• Ethereum (ETH/USD): ${formatPrice(markets.ethereum)}`,
    "",
    "⚽ Günün Favori Maçları:",
    matchText
  ].join("\n");
}

async function sendTelegramMessage(message) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text: message
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Telegram send failed: ${response.status} ${response.statusText} - ${text}`);
  }
}

async function main() {
  ensureEnv();

  const [weather, markets, matches] = await Promise.all([
    getWeather(),
    getMarkets(),
    getFavoriteMatches()
  ]);

  const message = formatTelegramMessage(weather, markets, matches);
  await sendTelegramMessage(message);

  console.log("Daily report sent successfully.");
}

main().catch((error) => {
  console.error("Daily report failed:", error);
  process.exitCode = 1;
});
