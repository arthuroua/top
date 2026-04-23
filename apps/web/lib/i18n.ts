export const SUPPORTED_LOCALES = ["en", "uk", "ru"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "uk";
export const LOCALE_COOKIE = "site_locale";

export function normalizeLocale(value: string | undefined | null): Locale {
  if (value && SUPPORTED_LOCALES.includes(value as Locale)) {
    return value as Locale;
  }
  return DEFAULT_LOCALE;
}

export const LANGUAGE_LABELS: Record<Locale, string> = {
  en: "EN",
  uk: "UK",
  ru: "RU"
};

export const dictionaries = {
  en: {
    siteName: "Auto Import Hub",
    siteSubtitle: "Auction intelligence for importers",
    nav: { search: "Search", catalog: "Catalog", watchlist: "Watchlist", reports: "Reports", calculator: "Calculator" },
    home: {
      chip: "Auction Intelligence",
      title: "A modern auction service for importers with VIN history, photos, specs, and margin tools",
      lead:
        "Fast VIN search, auction lot photos, import history, NHTSA configuration decoding, and importer math in one clean interface.",
      openSearch: "Open VIN search",
      openCatalog: "Browse brands and models",
      openCalculator: "Open importer toolkit",
      flowTitle: "Auction flow in one screen",
      flowLead:
        "From VIN to lot history and decision support, the product is built to help brokers and importers move faster with fewer mistakes.",
      flowButton: "Open SEO catalog",
      edgeTitle: "Not a clone, but a stronger product",
      edgeLead:
        "The visual language is cleaner, the workflow is faster, and the tooling is built for people who buy and move cars from U.S. auctions every week.",
      features: [
        {
          title: "VIN / Lot / URL Lookup",
          text: "One entry point for Copart, IAAI, and future sources without jumping between old pages."
        },
        {
          title: "Photos and Lot Timeline",
          text: "See pictures, sale status, bid events, and all known auction appearances in one place."
        },
        {
          title: "Import Snapshot History",
          text: "Every import is stored separately, so changes over time are visible instead of being overwritten."
        },
        {
          title: "Bid Decision Toolkit",
          text: "Calculate landed cost, safe max bid, and margin before you step into the auction."
        }
      ]
    },
    search: {
      chip: "Auction Search Console",
      title: "Search by VIN, lot number, or URL",
      lead:
        "Use one search box to open vehicle history, auction photos, import snapshots, NHTSA specs, and bid planning tools.",
      toHome: "Home",
      toCatalog: "Brands and models",
      label: "Search by VIN / lot / URL",
      placeholder: "5YJ3E1EA3JF053140 or auction lot number",
      submit: "Search",
      searching: "Searching...",
      helper: "VINs, lot numbers, and full auction URLs are supported.",
      empty: "Enter a VIN, lot number, or URL.",
      searchFailed: "Search failed.",
      vehicleFailed: "Failed to load vehicle card.",
      requestError: "Request failed.",
      kpiLots: "Lots found",
      kpiStatus: "Status",
      kpiLatestLot: "Latest lot",
      openVinPage: "Open VIN page",
      vehicleLabel: "Vehicle",
      titleBrand: "Title",
      noTitle: "No title data",
      lotPhotos: "Lot photos",
      noPhotos: "No valid image URLs are available for this lot yet.",
      lotCard: "Current lot card",
      noLots: "No lots found for this VIN.",
      source: "Source",
      lot: "Lot",
      saleDate: "Sale date",
      finalBid: "Final bid",
      location: "Location",
      auctionHistoryTitle: "Auction appearances",
      auctionHistoryLead: "Choose a lot to switch the gallery and current lot card.",
      noAuctionHistory: "No lots found for this VIN yet.",
      importHistoryTitle: "Import history",
      importHistoryLead: "Every update is stored separately. Total records:",
      noImportHistory: "Import history has not been collected for this VIN yet.",
      toolkitChip: "Importer Toolkit",
      toolkitTitle: "Quick profit plan for the lot",
      toolkitLead:
        "Estimate landed cost, target margin, safe max bid, and whether the current auction price still makes sense.",
      fields: {
        expectedSellUsd: "Expected sale price (USD)",
        targetMarginUsd: "Target margin (USD)",
        auctionFeesUsd: "Auction fees (USD)",
        logisticsUsd: "Logistics (USD)",
        customsUsd: "Customs (USD)",
        repairUsd: "Repairs (USD)",
        localCostsUsd: "Local costs (USD)"
      },
      stats: {
        currentBid: "Current bid",
        landedCost: "Landed cost at current bid",
        profit: "Profit at current bid",
        costsWithoutBid: "Costs without bid",
        safeMaxBid: "Safe max bid",
        delta: "Delta vs current bid"
      },
      badSignal: "The current bid is already above your safe limit. It is better to skip the lot or revise costs.",
      goodSignal: "The current bid is still within your safe limit for the selected target margin.",
      decoder: {
        title: "NHTSA VIN Decoder",
        lead: "Factory specs and safety equipment from the official NHTSA vPIC database.",
        source: "Open official NHTSA page",
        unavailable: "Decoder data is temporarily unavailable for this VIN.",
        note: "NHTSA note"
      },
      risk: {
        title: "Lot risk score",
        lead: "A quick signal for importers before going deeper into pricing and repair math.",
        score: "Risk score",
        level: "Risk level",
        low: "Low",
        medium: "Medium",
        high: "High",
        reasons: "What affects the score",
        titleReason: "The title type looks risky for resale or registration.",
        statusReason: "The current lot status needs extra checking before bidding.",
        multipleRunsReason: "The car appeared in auction multiple times, so demand may be weak or the car may have unresolved issues.",
        priceRunupReason: "The lot had multiple price or bid changes, so the economics may already be stretched.",
        missingImagesReason: "There are too few photos to judge damage confidently.",
        highBidReason: "The current price is already above the recent average for this VIN."
      },
      market: {
        title: "Market lower bound",
        lead: "A quick comps view to see the lower market floor and whether the lot still has room.",
        lowerBound: "Lower bound",
        median: "Median",
        average: "Average",
        comps: "Comps",
        noData: "Market comps are not available yet for this VIN.",
        similarity: "Similarity"
      }
    },
    auto: {
      pageChip: "VIN page",
      pageUnavailable: "Vehicle data for this VIN is temporarily unavailable",
      pageUnavailableLead:
        "The page stays live, but the backend is not responding right now. Once the API is available again, lots, photos, NHTSA specs, and import history will load automatically.",
      openSearch: "Open interactive search",
      openCatalog: "Open model catalog",
      heroChip: "VIN page",
      heroLead: "This VIN page combines auction history, official NHTSA specs, photos, and import snapshots without clutter.",
      openAnalysis: "Open interactive analysis",
      toCluster: "Open model cluster",
      lotsInBase: "Lots in base",
      averagePrice: "Average price",
      title: "Title",
      images: "Images",
      knowTitle: "What matters for this vehicle",
      lotsTitle: "Lot history",
      updateLogTitle: "Update log",
      faqTitle: "Questions and answers",
      practicalTitle: "Practical importer note",
      openCalculator: "Open profitability calculator",
      decoderTitle: "NHTSA equipment and configuration",
      decoderLead: "Official build and safety data from the U.S. regulator.",
      riskTitle: "Importer risk view",
      riskLead: "A compact lot risk signal based on title, lot activity, bid run-up, and photo coverage.",
      marketTitle: "Market lower bound",
      marketLead: "This helps understand the lower price floor from recent comparable auction results."
    },
    watchlist: {
      add: "Add to watchlist",
      remove: "Remove from watchlist",
      chip: "Watchlist",
      title: "Saved VINs and change tracking",
      lead: "Keep the cars you care about in one place and quickly see if the lot status, bid, or market floor has changed.",
      toSearch: "Open VIN search",
      toCatalog: "Open catalog",
      snapshot: "Watchlist snapshot",
      savedCars: "Saved cars",
      changesDetected: "Changes detected",
      loading: "Loading watchlist...",
      emptyTitle: "Your watchlist is empty",
      emptyLead: "Save vehicles from the VIN page or search results and they will appear here.",
      stable: "Stable",
      changed: "Changed",
      latestLot: "Latest lot",
      status: "Status",
      currentBid: "Current bid",
      lowerBound: "Lower bound",
      openVin: "Open VIN page",
      openAnalysis: "Open analysis"
    },
    cars: {
      hubChip: "Model catalog",
      hubTitle: "Popular brands and model pages for U.S. import",
      hubLead: "A managed catalog from your database that guides the user from brand to model and then to a specific VIN.",
      openSearch: "Open VIN search",
      openAdmin: "SEO admin",
      goBrand: "Open brand",
      openPage: "Open page",
      brandChip: "Brand page",
      brandAll: "Full catalog",
      brandSearch: "VIN search",
      brandSnapshot: "Brand snapshot",
      modelPages: "Model pages",
      status: "Status",
      decisionFlow: "Decision flow",
      active: "Active",
      paused: "Paused",
      clusterChip: "Model cluster",
      marketSnapshot: "Market snapshot",
      median: "Median",
      average: "Average",
      comps: "Comps",
      mode: "Mode",
      exact: "Exact",
      expanded: "Expanded",
      marketSales: "Market sales",
      openVin: "Open VIN"
    }
  },
  uk: {
    siteName: "Auto Import Hub",
    siteSubtitle: "Auction intelligence for importers",
    nav: { search: "Пошук", catalog: "Каталог", watchlist: "Watchlist", reports: "Звіти", calculator: "Калькулятор" },
    home: {
      chip: "Auction Intelligence",
      title: "Сучасний сервіс для пригону з VIN-історією, фото, комплектацією та калькулятором маржі",
      lead:
        "Швидкий VIN-пошук, фото аукціонних лотів, історія імпортів, декодування комплектації через NHTSA та інструменти для пригонщика в одному інтерфейсі.",
      openSearch: "Відкрити VIN-пошук",
      openCatalog: "Бренди та моделі",
      openCalculator: "Відкрити інструмент пригонщика",
      flowTitle: "Увесь аукціонний процес на одному екрані",
      flowLead:
        "Від VIN до історії лота і рішення по ставці: продукт зібраний так, щоб брокер або пригонщик працював швидше і спокійніше.",
      flowButton: "Відкрити SEO-каталог",
      edgeTitle: "Не копія, а сильніший продукт",
      edgeLead:
        "Візуально сервіс чистіший, сценарій роботи швидший, а інструменти заточені під тих, хто реально купує і везе авто зі США.",
      features: [
        {
          title: "VIN / Лот / URL пошук",
          text: "Одна точка входу для Copart, IAAI та майбутніх джерел без стрибків між старими сторінками."
        },
        {
          title: "Фото та таймлайн лота",
          text: "Бачиш фото, статус, події по ставках і всі відомі появи лота в одному місці."
        },
        {
          title: "Історія імпортних snapshot'ів",
          text: "Кожен імпорт зберігається окремо, тому зміни по лоту видно в часі, а не перезаписуються."
        },
        {
          title: "Інструмент рішення по ставці",
          text: "Розрахунок собівартості, безпечного max bid і маржі ще до входу в аукціон."
        }
      ]
    },
    search: {
      chip: "Auction Search Console",
      title: "Пошук по VIN, номеру лота або URL",
      lead:
        "Один пошук відкриває історію авто, фото лотів, імпортні snapshot'и, комплектацію NHTSA та інструменти для планування ставки.",
      toHome: "Головна",
      toCatalog: "Бренди та моделі",
      label: "Пошук по VIN / лоту / URL",
      placeholder: "5YJ3E1EA3JF053140 або номер аукціонного лота",
      submit: "Пошук",
      searching: "Пошук...",
      helper: "Підтримуються VIN, номер лота та повний URL аукціонної сторінки.",
      empty: "Введіть VIN, номер лота або URL.",
      searchFailed: "Не вдалося виконати пошук.",
      vehicleFailed: "Не вдалося завантажити картку авто.",
      requestError: "Помилка запиту.",
      kpiLots: "Знайдено лотів",
      kpiStatus: "Статус",
      kpiLatestLot: "Останній лот",
      openVinPage: "Відкрити VIN-сторінку",
      vehicleLabel: "Автомобіль",
      titleBrand: "Title",
      noTitle: "Немає даних по title",
      lotPhotos: "Фото лота",
      noPhotos: "Для цього лота поки немає валідних фото URL.",
      lotCard: "Картка поточного лота",
      noLots: "Лоти по цьому VIN поки не знайдені.",
      source: "Джерело",
      lot: "Лот",
      saleDate: "Дата продажу",
      finalBid: "Фінальна ставка",
      location: "Локація",
      auctionHistoryTitle: "Історія аукціонних появ",
      auctionHistoryLead: "Обирай лот, щоб перемкнути галерею та картку поточного лота.",
      noAuctionHistory: "По VIN поки немає лотів.",
      importHistoryTitle: "Історія імпортів",
      importHistoryLead: "Кожне оновлення зберігається окремо. Усього записів:",
      noImportHistory: "Історія імпортів ще не зібрана для цього VIN.",
      toolkitChip: "Importer Toolkit",
      toolkitTitle: "Швидкий план прибутку по лоту",
      toolkitLead:
        "Показує собівартість, цільову маржу, безпечний max bid і чи проходить поточна ставка по економіці.",
      fields: {
        expectedSellUsd: "Очікуваний продаж (USD)",
        targetMarginUsd: "Цільова маржа (USD)",
        auctionFeesUsd: "Аукціонні збори (USD)",
        logisticsUsd: "Логістика (USD)",
        customsUsd: "Митниця (USD)",
        repairUsd: "Ремонт (USD)",
        localCostsUsd: "Локальні витрати (USD)"
      },
      stats: {
        currentBid: "Поточна ставка",
        landedCost: "Собівартість при поточній ставці",
        profit: "Прибуток при поточній ставці",
        costsWithoutBid: "Витрати без ставки",
        safeMaxBid: "Безпечний Max Bid",
        delta: "Різниця до поточного bid"
      },
      badSignal: "Поточний bid уже вищий за твій безпечний ліміт. Краще пропустити лот або переглянути витрати.",
      goodSignal: "Поточний bid ще в межах безпечного ліміту по заданій маржі.",
      decoder: {
        title: "NHTSA VIN Decoder",
        lead: "Заводська комплектація та системи безпеки з офіційної бази NHTSA vPIC.",
        source: "Відкрити офіційну сторінку NHTSA",
        unavailable: "Дані декодера тимчасово недоступні для цього VIN.",
        note: "Примітка NHTSA"
      },
      risk: {
        title: "Ризик лота",
        lead: "Швидкий сигнал для пригонщика перед глибшим розрахунком ремонту й економіки.",
        score: "Risk score",
        level: "Рівень ризику",
        low: "Низький",
        medium: "Середній",
        high: "Високий",
        reasons: "Що впливає на оцінку",
        titleReason: "Тип title виглядає ризиково для перепродажу або реєстрації.",
        statusReason: "Поточний статус лота треба додатково перевірити перед ставкою.",
        multipleRunsReason: "Авто з'являлося на аукціоні кілька разів, тому попит міг бути слабким або є невирішені проблеми.",
        priceRunupReason: "По лоту було багато змін ціни або bid-подій, тому економіка може бути вже перегріта.",
        missingImagesReason: "Фото замало, щоб впевнено оцінити пошкодження.",
        highBidReason: "Поточна ціна вже вища за недавню середню по цьому VIN."
      },
      market: {
        title: "Нижня межа ринку",
        lead: "Швидкий блок по компах, щоб бачити нижню межу ринку і чи ще є запас по лоту.",
        lowerBound: "Нижня межа",
        median: "Медіана",
        average: "Середня",
        comps: "Компи",
        noData: "Для цього VIN поки немає ринкових компів.",
        similarity: "Схожість"
      }
    },
    auto: {
      pageChip: "VIN сторінка",
      pageUnavailable: "Дані по цьому VIN тимчасово недоступні",
      pageUnavailableLead:
        "Сторінка не падає, але бекенд зараз не відповідає. Як тільки API знову стане доступним, тут автоматично підтягнуться лоти, фото, NHTSA-специфікація та історія імпортів.",
      openSearch: "Відкрити інтерактивний пошук",
      openCatalog: "Каталог моделей",
      heroChip: "VIN сторінка",
      heroLead: "Тут зібрані аукціонна історія, офіційна комплектація NHTSA, фото та імпортні snapshot'и без інформаційного шуму.",
      openAnalysis: "Відкрити інтерактивний аналіз",
      toCluster: "Відкрити кластер моделі",
      lotsInBase: "Лотів у базі",
      averagePrice: "Середня ціна",
      title: "Title",
      images: "Фото",
      knowTitle: "Що важливо знати по цьому авто",
      lotsTitle: "Історія лотів",
      updateLogTitle: "Лог оновлень",
      faqTitle: "Питання та відповіді",
      practicalTitle: "Практична порада для пригонщика",
      openCalculator: "Відкрити калькулятор прибутковості",
      decoderTitle: "Комплектація та безпека NHTSA",
      decoderLead: "Офіційні заводські дані та системи безпеки з бази американського регулятора.",
      riskTitle: "Ризик-оцінка для пригонщика",
      riskLead: "Короткий ризик-сигнал по лоту на основі title, активності лота, розгону ставок і покриття фото.",
      marketTitle: "Нижня межа ринку",
      marketLead: "Допомагає зрозуміти нижній ціновий поріг за недавніми схожими аукціонними продажами."
    },
    watchlist: {
      add: "Додати в watchlist",
      remove: "Прибрати з watchlist",
      chip: "Watchlist",
      title: "Збережені VIN і відстеження змін",
      lead: "Тримай важливі авто в одному місці й швидко бач, чи змінився статус лота, bid або нижня межа ринку.",
      toSearch: "Відкрити VIN-пошук",
      toCatalog: "Відкрити каталог",
      snapshot: "Стан watchlist",
      savedCars: "Збережено авто",
      changesDetected: "Знайдено змін",
      loading: "Завантажуємо watchlist...",
      emptyTitle: "Watchlist поки порожній",
      emptyLead: "Зберігай авто з VIN-сторінки або з пошуку, і вони з'являться тут.",
      stable: "Без змін",
      changed: "Є зміни",
      latestLot: "Останній лот",
      status: "Статус",
      currentBid: "Поточний bid",
      lowerBound: "Нижня межа",
      openVin: "Відкрити VIN-сторінку",
      openAnalysis: "Відкрити аналіз"
    },
    cars: {
      hubChip: "Каталог моделей",
      hubTitle: "Популярні бренди та модельні сторінки для пригону зі США",
      hubLead: "Керований каталог із бази даних, який веде користувача від бренду до моделі, а далі до конкретного VIN.",
      openSearch: "Відкрити VIN-пошук",
      openAdmin: "SEO адмінка",
      goBrand: "Перейти до бренду",
      openPage: "Відкрити сторінку",
      brandChip: "Сторінка бренду",
      brandAll: "Весь каталог",
      brandSearch: "VIN-пошук",
      brandSnapshot: "Стан бренду",
      modelPages: "Сторінок моделей",
      status: "Статус",
      decisionFlow: "Ланцюжок рішення",
      active: "Активна",
      paused: "Пауза",
      clusterChip: "Кластер моделі",
      marketSnapshot: "Ринковий snapshot",
      median: "Медіана",
      average: "Середня",
      comps: "Компи",
      mode: "Режим",
      exact: "Точний",
      expanded: "Розширений",
      marketSales: "Ринкові продажі",
      openVin: "Відкрити VIN"
    }
  },
  ru: {
    siteName: "Auto Import Hub",
    siteSubtitle: "Auction intelligence for importers",
    nav: { search: "Поиск", catalog: "Каталог", watchlist: "Watchlist", reports: "Отчёты", calculator: "Калькулятор" },
    home: {
      chip: "Auction Intelligence",
      title: "Современный сервис для пригона с VIN-историей, фото, комплектацией и калькулятором маржи",
      lead:
        "Быстрый VIN-поиск, фото аукционных лотов, история импортов, декодирование комплектации через NHTSA и инструменты для пригонщика в одном интерфейсе.",
      openSearch: "Открыть VIN-поиск",
      openCatalog: "Бренды и модели",
      openCalculator: "Открыть инструмент импортёра",
      flowTitle: "Весь аукционный процесс на одном экране",
      flowLead:
        "От VIN до истории лота и решения по ставке: продукт собран так, чтобы брокер или импортёр работал быстрее и спокойнее.",
      flowButton: "Открыть SEO-каталог",
      edgeTitle: "Не копия, а более сильный продукт",
      edgeLead:
        "Визуально сервис чище, сценарий работы быстрее, а инструменты заточены под тех, кто реально покупает и везёт авто из США.",
      features: [
        {
          title: "VIN / Лот / URL поиск",
          text: "Одна точка входа для Copart, IAAI и будущих источников без прыжков между старыми страницами."
        },
        {
          title: "Фото и таймлайн лота",
          text: "Видно фото, статус, события по ставкам и все известные появления лота в одном месте."
        },
        {
          title: "История импортных snapshot'ов",
          text: "Каждый импорт сохраняется отдельно, поэтому изменения по лоту видны во времени, а не перезаписываются."
        },
        {
          title: "Инструмент решения по ставке",
          text: "Расчёт себестоимости, безопасного max bid и маржи ещё до входа в аукцион."
        }
      ]
    },
    search: {
      chip: "Auction Search Console",
      title: "Поиск по VIN, номеру лота или URL",
      lead:
        "Один поиск открывает историю авто, фото лотов, импортные snapshot'ы, комплектацию NHTSA и инструменты для планирования ставки.",
      toHome: "Главная",
      toCatalog: "Бренды и модели",
      label: "Поиск по VIN / лоту / URL",
      placeholder: "5YJ3E1EA3JF053140 или номер аукционного лота",
      submit: "Поиск",
      searching: "Поиск...",
      helper: "Поддерживаются VIN, номер лота и полный URL аукционной страницы.",
      empty: "Введите VIN, номер лота или URL.",
      searchFailed: "Не удалось выполнить поиск.",
      vehicleFailed: "Не удалось загрузить карточку авто.",
      requestError: "Ошибка запроса.",
      kpiLots: "Найдено лотов",
      kpiStatus: "Статус",
      kpiLatestLot: "Последний лот",
      openVinPage: "Открыть VIN-страницу",
      vehicleLabel: "Автомобиль",
      titleBrand: "Title",
      noTitle: "Нет данных по title",
      lotPhotos: "Фото лота",
      noPhotos: "Для этого лота пока нет валидных фото URL.",
      lotCard: "Карточка текущего лота",
      noLots: "Лоты по этому VIN пока не найдены.",
      source: "Источник",
      lot: "Лот",
      saleDate: "Дата продажи",
      finalBid: "Финальная ставка",
      location: "Локация",
      auctionHistoryTitle: "История аукционных появлений",
      auctionHistoryLead: "Выбери лот, чтобы переключить галерею и карточку текущего лота.",
      noAuctionHistory: "По VIN пока нет лотов.",
      importHistoryTitle: "История импортов",
      importHistoryLead: "Каждое обновление сохраняется отдельно. Всего записей:",
      noImportHistory: "История импортов ещё не собрана для этого VIN.",
      toolkitChip: "Importer Toolkit",
      toolkitTitle: "Быстрый план прибыли по лоту",
      toolkitLead:
        "Показывает себестоимость, целевую маржу, безопасный max bid и проходит ли текущая ставка по экономике.",
      fields: {
        expectedSellUsd: "Ожидаемая продажа (USD)",
        targetMarginUsd: "Целевая маржа (USD)",
        auctionFeesUsd: "Аукционные сборы (USD)",
        logisticsUsd: "Логистика (USD)",
        customsUsd: "Таможня (USD)",
        repairUsd: "Ремонт (USD)",
        localCostsUsd: "Локальные расходы (USD)"
      },
      stats: {
        currentBid: "Текущая ставка",
        landedCost: "Себестоимость при текущей ставке",
        profit: "Прибыль при текущей ставке",
        costsWithoutBid: "Расходы без ставки",
        safeMaxBid: "Безопасный Max Bid",
        delta: "Разница к текущему bid"
      },
      badSignal: "Текущий bid уже выше твоего безопасного лимита. Лучше пропустить лот или пересмотреть расходы.",
      goodSignal: "Текущий bid ещё в пределах безопасного лимита по заданной марже.",
      decoder: {
        title: "NHTSA VIN Decoder",
        lead: "Заводская комплектация и системы безопасности из официальной базы NHTSA vPIC.",
        source: "Открыть официальную страницу NHTSA",
        unavailable: "Данные декодера временно недоступны для этого VIN.",
        note: "Примечание NHTSA"
      },
      risk: {
        title: "Риск лота",
        lead: "Быстрый сигнал для пригонщика перед более глубоким расчётом ремонта и экономики.",
        score: "Risk score",
        level: "Уровень риска",
        low: "Низкий",
        medium: "Средний",
        high: "Высокий",
        reasons: "Что влияет на оценку",
        titleReason: "Тип title выглядит рискованно для перепродажи или регистрации.",
        statusReason: "Текущий статус лота нужно дополнительно проверить перед ставкой.",
        multipleRunsReason: "Авто появлялось на аукционе несколько раз, поэтому спрос мог быть слабым или есть нерешённые проблемы.",
        priceRunupReason: "По лоту было много изменений цены или bid-событий, поэтому экономика может быть уже перегрета.",
        missingImagesReason: "Фото слишком мало, чтобы уверенно оценить повреждения.",
        highBidReason: "Текущая цена уже выше недавней средней по этому VIN."
      },
      market: {
        title: "Нижняя граница рынка",
        lead: "Быстрый блок по компам, чтобы видеть нижнюю границу рынка и есть ли ещё запас по лоту.",
        lowerBound: "Нижняя граница",
        median: "Медиана",
        average: "Средняя",
        comps: "Компы",
        noData: "Для этого VIN пока нет рыночных компов.",
        similarity: "Схожесть"
      }
    },
    auto: {
      pageChip: "VIN страница",
      pageUnavailable: "Данные по этому VIN временно недоступны",
      pageUnavailableLead:
        "Страница не падает, но backend сейчас не отвечает. Как только API снова станет доступным, здесь автоматически подтянутся лоты, фото, NHTSA-спеки и история импортов.",
      openSearch: "Открыть интерактивный поиск",
      openCatalog: "Каталог моделей",
      heroChip: "VIN страница",
      heroLead: "Здесь собраны аукционная история, официальная комплектация NHTSA, фото и импортные snapshot'ы без информационного шума.",
      openAnalysis: "Открыть интерактивный анализ",
      toCluster: "Открыть кластер модели",
      lotsInBase: "Лотов в базе",
      averagePrice: "Средняя цена",
      title: "Title",
      images: "Фото",
      knowTitle: "Что важно знать по этому авто",
      lotsTitle: "История лотов",
      updateLogTitle: "Лог обновлений",
      faqTitle: "Вопросы и ответы",
      practicalTitle: "Практическая заметка для пригонщика",
      openCalculator: "Открыть калькулятор прибыльности",
      decoderTitle: "Комплектация и безопасность NHTSA",
      decoderLead: "Официальные заводские данные и системы безопасности из базы американского регулятора.",
      riskTitle: "Риск-оценка для пригонщика",
      riskLead: "Короткий риск-сигнал по лоту на основе title, активности лота, разгона ставок и покрытия фото.",
      marketTitle: "Нижняя граница рынка",
      marketLead: "Помогает понять нижний ценовой порог по недавним похожим аукционным продажам."
    },
    watchlist: {
      add: "Добавить в watchlist",
      remove: "Убрать из watchlist",
      chip: "Watchlist",
      title: "Сохранённые VIN и отслеживание изменений",
      lead: "Держи важные авто в одном месте и быстро смотри, изменился ли статус лота, bid или нижняя граница рынка.",
      toSearch: "Открыть VIN-поиск",
      toCatalog: "Открыть каталог",
      snapshot: "Состояние watchlist",
      savedCars: "Сохранено авто",
      changesDetected: "Найдено изменений",
      loading: "Загрузка watchlist...",
      emptyTitle: "Watchlist пока пуст",
      emptyLead: "Сохраняй авто со страницы VIN или из поиска, и они появятся здесь.",
      stable: "Без изменений",
      changed: "Есть изменения",
      latestLot: "Последний лот",
      status: "Статус",
      currentBid: "Текущий bid",
      lowerBound: "Нижняя граница",
      openVin: "Открыть VIN-страницу",
      openAnalysis: "Открыть анализ"
    },
    cars: {
      hubChip: "Каталог моделей",
      hubTitle: "Популярные бренды и модельные страницы для импорта из США",
      hubLead: "Управляемый каталог из базы данных, который ведёт пользователя от бренда к модели, а затем к конкретному VIN.",
      openSearch: "Открыть VIN-поиск",
      openAdmin: "SEO админка",
      goBrand: "Открыть бренд",
      openPage: "Открыть страницу",
      brandChip: "Страница бренда",
      brandAll: "Весь каталог",
      brandSearch: "VIN-поиск",
      brandSnapshot: "Снимок бренда",
      modelPages: "Страниц моделей",
      status: "Статус",
      decisionFlow: "Цепочка решения",
      active: "Активна",
      paused: "Пауза",
      clusterChip: "Кластер модели",
      marketSnapshot: "Снимок рынка",
      median: "Медиана",
      average: "Средняя",
      comps: "Компы",
      mode: "Режим",
      exact: "Точный",
      expanded: "Расширенный",
      marketSales: "Рыночные продажи",
      openVin: "Открыть VIN"
    }
  }
} as const;

export function getDictionary(locale: Locale) {
  return dictionaries[locale];
}
