export type SeoBrand = {
  make: string;
  title: string;
  teaser: string;
};

export type SeoCluster = {
  make: string;
  model: string;
  year: number;
  title: string;
  teaser: string;
};

export const SEO_BRANDS: SeoBrand[] = [
  { make: "Acura", title: "Acura зі США", teaser: "Преміальний японський бренд із помірною конкуренцією та шансом взяти живий лот без перегріву ціни." },
  { make: "Alfa Romeo", title: "Alfa Romeo зі США", teaser: "Нішевий бренд для точкового відбору, де вирішують стан кузова, електроніка і реальна ліквідність на місцевому ринку." },
  { make: "Audi", title: "Audi зі США", teaser: "Сильний попит і хороший середній чек, але помилка в ремонті тут швидко з'їдає всю маржу." },
  { make: "BMW", title: "BMW зі США", teaser: "Бренд із високим інтересом покупців, де важливо дуже точно рахувати ремонт, логістику і кінцеву ціну продажу." },
  { make: "Buick", title: "Buick зі США", teaser: "Недооцінений сегмент для пригону, де часто можна знайти спокійну маржу при правильному виборі лота." },
  { make: "Cadillac", title: "Cadillac зі США", teaser: "Преміум-сегмент із високою потенційною маржею, але й з більшими ризиками дорогих пошкоджень." },
  { make: "Chevrolet", title: "Chevrolet зі США", teaser: "Масовий бренд із великим вибором лотів і широким діапазоном моделей для різних бюджетів." },
  { make: "Chrysler", title: "Chrysler зі США", teaser: "Напрямок для вибіркових покупок, де критично важливі стан коробки, кузова і ціна входу." },
  { make: "Dodge", title: "Dodge зі США", teaser: "Популярний сегмент із емоційним попитом, де особливо важливо не помилитися з бюджетом ремонту." },
  { make: "Fiat", title: "Fiat зі США", teaser: "Компактний сегмент, який має сенс тільки при дуже дисциплінованій ціні входу." },
  { make: "Ford", title: "Ford зі США", teaser: "Широкий вибір лотів і великий розкид по пошкодженнях, тому без аналітики ставок легко зайти в слабку маржу." },
  { make: "Genesis", title: "Genesis зі США", teaser: "Сучасний преміум із хорошим запасом маржі, якщо лот не має складних електронних або силових пошкоджень." },
  { make: "GMC", title: "GMC зі США", teaser: "Пікапи та SUV з міцним попитом, де треба контролювати логістику, вагу і бюджет відновлення." },
  { make: "Honda", title: "Honda зі США", teaser: "Один із найстабільніших напрямків для пригону: зрозумілий ремонт, попит і ліквідність на українському ринку." },
  { make: "Hyundai", title: "Hyundai зі США", teaser: "Практичний бренд для середнього бюджету, де добре працює масовий попит і прогнозована собівартість." },
  { make: "Infiniti", title: "Infiniti зі США", teaser: "Нішевий преміум, де вигода часто залежить від комплектації, стану кузова і місцевого попиту." },
  { make: "Jaguar", title: "Jaguar зі США", teaser: "Бренд з потенційно високою маржею, але й з високим ризиком по сервісу та запчастинах." },
  { make: "Jeep", title: "Jeep зі США", teaser: "SUV-сегмент із хорошим попитом, але з великою різницею між вдалою і невдалою ставкою." },
  { make: "Kia", title: "Kia зі США", teaser: "Сильний масовий бренд, де важливо швидко відсікати лоти з поганою економікою ремонту." },
  { make: "Land Rover", title: "Land Rover зі США", teaser: "Високомаржинальний бренд тільки для дуже точного відбору лотів і консервативного розрахунку витрат." },
  { make: "Lexus", title: "Lexus зі США", teaser: "Ліквідний преміум-сегмент із хорошою репутацією, де правильно підібраний лот дає стабільну маржу." },
  { make: "Lincoln", title: "Lincoln зі США", teaser: "Нішевий сегмент, де важливі не лише пошкодження, а й реальний попит на локальному ринку." },
  { make: "Mazda", title: "Mazda зі США", teaser: "Один із найзрозуміліших брендів для пригону, якщо не перегріти ставку на аукціоні." },
  { make: "Mercedes-Benz", title: "Mercedes-Benz зі США", teaser: "Преміальний бренд із великим інтересом, але дуже чутливий до дорогого ремонту та електроніки." },
  { make: "MINI", title: "MINI зі США", teaser: "Нішеві моделі з лояльною аудиторією, де вигода сильно залежить від точної ціни входу." },
  { make: "Mitsubishi", title: "Mitsubishi зі США", teaser: "Практичний бренд для бюджетного сегмента, де ключову роль відіграє ліквідність конкретної моделі." },
  { make: "Nissan", title: "Nissan зі США", teaser: "Один із наймасовіших напрямків для пригону, де треба уважно дивитися на трансмісію і реальну маржу." },
  { make: "Polestar", title: "Polestar зі США", teaser: "Новий електросегмент, де вирішують батарея, кузов і перспектива перепродажу після ремонту." },
  { make: "Porsche", title: "Porsche зі США", teaser: "Маржинальний бренд лише для дисциплінованого відбору лотів і дуже точного прорахунку ризиків." },
  { make: "RAM", title: "RAM зі США", teaser: "Пікапи з хорошим попитом, де вирішують логістика, стан рами і реальна ціна продажу на місцевому ринку." },
  { make: "Rivian", title: "Rivian зі США", teaser: "Новий електричний сегмент із великим інтересом, але поки що з високою ціною помилки по ремонту." },
  { make: "Subaru", title: "Subaru зі США", teaser: "Стабільний бренд для тих, хто вміє рахувати повний бюджет ремонту і знає попит на AWD-моделі." },
  { make: "Tesla", title: "Tesla зі США", teaser: "Електромобілі з високим попитом, де критично правильно оцінити батарею, кузов і фінальну маржу після ремонту." },
  { make: "Toyota", title: "Toyota зі США", teaser: "Практичний сегмент із прогнозованою собівартістю, де найважливіше не переплатити на вході." },
  { make: "Volkswagen", title: "Volkswagen зі США", teaser: "Популярний європейський бренд, де вигода залежить від балансу між ціною входу і вартістю відновлення." },
  { make: "Volvo", title: "Volvo зі США", teaser: "Надійний преміум-сегмент, де увагу треба приділяти електроніці, безпеці та бюджету ремонту." }
];

export const SEO_CLUSTERS: SeoCluster[] = [
  { make: "Tesla", model: "Model 3", year: 2022, title: "Tesla Model 3 2022 зі США", teaser: "Середній діапазон аукціонних цін, типові пошкодження і орієнтир по маржі для пригону." },
  { make: "Tesla", model: "Model Y", year: 2021, title: "Tesla Model Y 2021 з Copart та IAAI", teaser: "Дані по лотах, динаміка ставок і практичний чекліст перед покупкою." },
  { make: "Ford", model: "Escape", year: 2020, title: "Ford Escape 2020: чи вигідний пригін", teaser: "Орієнтир по ціні входу, ремонту і фінальній собівартості під український ринок." },
  { make: "Nissan", model: "Rogue", year: 2021, title: "Nissan Rogue 2021: аукціонна аналітика", teaser: "Фото, лоти і розрахунок безпечної ставки з урахуванням доставки та митниці." },
  { make: "Volkswagen", model: "Passat", year: 2018, title: "Volkswagen Passat 2018 зі страхових аукціонів", teaser: "Коли Passat зі США дійсно вигідний, а коли лот краще пропустити." },
  { make: "BMW", model: "X5", year: 2019, title: "BMW X5 2019: ризики і ціни", teaser: "Сценарії по бюджету пригону, ремонту та фінальній маржі після розмитнення." },
  { make: "Audi", model: "Q5", year: 2019, title: "Audi Q5 2019: ринок лотів США", teaser: "Які ціни зустрічаються в лотах і як не піти в мінус по ремонту." },
  { make: "Hyundai", model: "Elantra", year: 2019, title: "Hyundai Elantra 2019 для пригону", teaser: "Практичний гід по бюджету входу, частих дефектах і рентабельності продажу." },
  { make: "Kia", model: "Niro", year: 2020, title: "Kia Niro 2020: гібридний сегмент", teaser: "Середні ціни на лоти і як рахувати прибуток для гібридів з аукціону." },
  { make: "Jeep", model: "Cherokee", year: 2019, title: "Jeep Cherokee 2019: огляд лотів", teaser: "Порівняння продажів, ризиків і фінальної собівартості для реального ринку." },
  { make: "Honda", model: "Accord", year: 2018, title: "Honda Accord 2018: аналітика пригону", teaser: "Чесний огляд цін лотів і орієнтир по безпечній ставці на аукціоні." },
  { make: "Toyota", model: "Camry", year: 2020, title: "Toyota Camry 2020: ринок і маржа", teaser: "Який бюджет потрібен для вигідного пригону Camry зі США у 2026 році." }
];

export function slugify(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export function brandHref(make: string): string {
  return `/cars/${slugify(make)}`;
}

export function clusterHref(cluster: Pick<SeoCluster, "make" | "model" | "year">): string {
  return `/cars/${slugify(cluster.make)}/${slugify(cluster.model)}/${cluster.year}`;
}

export type ModelMenuItem = {
  make: string;
  models: string[];
};

export const SEO_MODEL_MENU: ModelMenuItem[] = [
  { make: "BMW", models: ["X1", "X3", "X5", "X7", "3 Series", "5 Series", "7 Series", "i3", "i4", "i7", "iX"] },
  { make: "Audi", models: ["A3", "A4", "A5", "A6", "Q3", "Q5", "Q7", "Q8", "e-tron", "Q4 e-tron"] },
  { make: "Mercedes-Benz", models: ["A-Class", "C-Class", "E-Class", "GLA", "GLB", "GLC", "GLE", "GLS", "S-Class", "EQE", "EQS"] },
  { make: "Tesla", models: ["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"] },
  { make: "Toyota", models: ["Camry", "Corolla", "RAV4", "Highlander", "Prius", "Tacoma", "Tundra", "Sienna", "Venza"] },
  { make: "Honda", models: ["Accord", "Civic", "CR-V", "HR-V", "Pilot", "Odyssey", "Ridgeline"] },
  { make: "Nissan", models: ["Rogue", "Rogue Sport", "Altima", "Sentra", "Leaf", "Murano", "Pathfinder", "Frontier", "Ariya"] },
  { make: "Volkswagen", models: ["Passat", "Jetta", "Tiguan", "Atlas", "Golf"] },
  { make: "Hyundai", models: ["Elantra", "Sonata", "Tucson", "Santa Fe", "Kona", "Palisade", "Ioniq 5", "Ioniq 6"] },
  { make: "Kia", models: ["Niro", "Sportage", "Sorento", "Optima", "K5", "Telluride", "EV6", "EV9"] },
  { make: "Jeep", models: ["Cherokee", "Grand Cherokee", "Compass", "Wrangler", "Renegade", "Gladiator", "Wagoneer"] },
  { make: "Ford", models: ["Edge", "Escape", "Fusion", "Explorer", "Expedition", "F-150", "Maverick", "Mustang", "Mustang Mach-E"] },
  { make: "Chevrolet", models: ["Bolt EV", "Bolt EUV", "Malibu", "Equinox", "Traverse", "Tahoe", "Suburban", "Silverado", "Colorado"] },
  { make: "Lexus", models: ["RX", "NX", "UX", "ES", "IS", "GX", "LX"] },
  { make: "Mazda", models: ["Mazda3", "Mazda6", "CX-3", "CX-30", "CX-5", "CX-50", "CX-9", "CX-90"] },
  { make: "Subaru", models: ["Forester", "Outback", "Impreza", "Legacy", "Crosstrek", "Ascent", "WRX"] },
  { make: "Porsche", models: ["Cayenne", "Macan", "Panamera", "Taycan", "911"] },
  { make: "Volvo", models: ["S60", "S90", "XC40", "XC60", "XC90", "C40"] },
  { make: "Rivian", models: ["R1T", "R1S"] },
  { make: "Polestar", models: ["2", "3", "4"] },
  { make: "GMC", models: ["Terrain", "Acadia", "Yukon", "Sierra", "Canyon", "Hummer EV"] },
  { make: "RAM", models: ["1500", "2500", "3500", "ProMaster"] },
  { make: "Cadillac", models: ["XT4", "XT5", "XT6", "Escalade", "Lyriq"] },
  { make: "Lincoln", models: ["Corsair", "Nautilus", "Aviator", "Navigator"] },
  { make: "Acura", models: ["ILX", "TLX", "RDX", "MDX"] },
  { make: "Infiniti", models: ["Q50", "QX50", "QX60", "QX80"] },
  { make: "MINI", models: ["Cooper", "Countryman", "Clubman"] }
];

export type CatalogMenuSection = {
  title: string;
  links: Array<{ label: string; href: string }>;
};

export const CATALOG_MENU_SECTIONS: CatalogMenuSection[] = [
  {
    title: "Top brands",
    links: ["Acura", "Audi", "BMW", "Chevrolet", "Ford", "Honda", "Hyundai", "Kia", "Lexus", "Mercedes-Benz", "Nissan", "Toyota", "Volkswagen"].map((make) => ({
      label: make,
      href: brandHref(make),
    })),
  },
  {
    title: "Electric",
    links: [
      ["Tesla", "Model 3"],
      ["Tesla", "Model Y"],
      ["Chevrolet", "Bolt EV"],
      ["Ford", "Mustang Mach-E"],
      ["Hyundai", "Ioniq 5"],
      ["Kia", "EV6"],
      ["Nissan", "Leaf"],
      ["Porsche", "Taycan"],
      ["Rivian", "R1T"],
      ["Polestar", "2"],
    ].map(([make, model]) => ({ label: `${make} ${model}`, href: modelHref(make, model) })),
  },
  {
    title: "SUVs",
    links: [
      ["Ford", "Edge"],
      ["Ford", "Explorer"],
      ["Nissan", "Rogue"],
      ["Toyota", "RAV4"],
      ["Honda", "CR-V"],
      ["Mazda", "CX-5"],
      ["BMW", "X5"],
      ["Audi", "Q5"],
      ["Mercedes-Benz", "GLE"],
      ["Jeep", "Grand Cherokee"],
    ].map(([make, model]) => ({ label: `${make} ${model}`, href: modelHref(make, model) })),
  },
  {
    title: "Pickups",
    links: [
      ["Ford", "F-150"],
      ["Ford", "Maverick"],
      ["Chevrolet", "Silverado"],
      ["Chevrolet", "Colorado"],
      ["Toyota", "Tacoma"],
      ["Toyota", "Tundra"],
      ["RAM", "1500"],
      ["GMC", "Sierra"],
      ["Rivian", "R1T"],
    ].map(([make, model]) => ({ label: `${make} ${model}`, href: modelHref(make, model) })),
  },
];

export function modelHref(make: string, model: string): string {
  return `/cars/${slugify(make)}/${slugify(model)}`;
}

export function findModelsForMake(make: string): string[] {
  return SEO_MODEL_MENU.find((item) => item.make.toLowerCase() === make.toLowerCase())?.models || [];
}

export function findModelBySlugs(makeSlug: string, modelSlug: string): { make: string; model: string } | null {
  const makeEntry = SEO_MODEL_MENU.find((item) => slugify(item.make) === makeSlug);
  if (!makeEntry) return null;
  const model = makeEntry.models.find((item) => slugify(item) === modelSlug);
  return model ? { make: makeEntry.make, model } : null;
}

export function findClusterBySlugs(makeSlug: string, modelSlug: string, year: number): SeoCluster | undefined {
  return SEO_CLUSTERS.find(
    (item) => slugify(item.make) === makeSlug && slugify(item.model) === modelSlug && item.year === year
  );
}

export function findBrandBySlug(makeSlug: string): SeoBrand | undefined {
  return SEO_BRANDS.find((item) => slugify(item.make) === makeSlug);
}

export function getBrandClusters(make: string): SeoCluster[] {
  return SEO_CLUSTERS.filter((item) => item.make.toLowerCase() === make.toLowerCase());
}

export function readableFromSlug(value: string): string {
  const decoded = decodeURIComponent(value).replace(/-/g, " ").trim();
  if (!decoded) return value;
  return decoded
    .split(/\s+/)
    .map((token) => {
      if (/^\d+$/.test(token)) return token;
      if (/^[a-z]\d+$/i.test(token)) return token.toUpperCase();
      if (token.length <= 2) return token.toUpperCase();
      return token[0].toUpperCase() + token.slice(1).toLowerCase();
    })
    .join(" ");
}
