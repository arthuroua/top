"use client";

import Link from "next/link";
import { useState } from "react";

import { modelPageHref } from "../lib/seoApi";

type BrandOption = {
  make: string;
  slugPath: string;
  models: string[];
};

type Props = {
  brands: BrandOption[];
  labels: {
    chip: string;
    title: string;
    lead: string;
    make: string;
    model: string;
    chooseMake: string;
    chooseModel: string;
    openBrand: string;
    openModel: string;
  };
};

export function CarsQuickPicker({ brands, labels }: Props) {
  const [selectedMake, setSelectedMake] = useState("");
  const [selectedModel, setSelectedModel] = useState("");

  const activeBrand = brands.find((item) => item.make === selectedMake) ?? null;
  const modelOptions = activeBrand?.models ?? [];
  const brandHref = activeBrand ? `/cars/${activeBrand.slugPath}` : "/cars";
  const modelHref = activeBrand && selectedModel ? modelPageHref(activeBrand.make, selectedModel) : brandHref;

  function handleMakeChange(nextMake: string) {
    setSelectedMake(nextMake);
    const nextBrand = brands.find((item) => item.make === nextMake);
    setSelectedModel(nextBrand?.models[0] ?? "");
  }

  return (
    <section className="panel carsQuickPicker">
      <div className="carsQuickPickerIntro">
        <h2>{labels.title}</h2>
      </div>

      <div className="carsQuickPickerPanel">
        <label className="carsQuickPickerField">
          <select value={selectedMake} onChange={(event) => handleMakeChange(event.target.value)}>
            <option value="">{labels.chooseMake}</option>
            {brands.map((brand) => (
              <option key={brand.make} value={brand.make}>
                {brand.make}
              </option>
            ))}
          </select>
        </label>

        <label className="carsQuickPickerField">
          <select
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
            disabled={!selectedMake || modelOptions.length === 0}
          >
            <option value="">{labels.chooseModel}</option>
            {modelOptions.map((model) => (
              <option key={`${selectedMake}-${model}`} value={model}>
                {model}
              </option>
            ))}
          </select>
        </label>

        <div className="carsQuickPickerActions">
          <Link href={modelHref} className={`button ${!selectedModel ? "isDisabledLink" : ""}`} aria-disabled={!selectedModel}>
            {labels.openModel}
          </Link>
          <Link href={brandHref} className={`carsQuickPickerTextLink ${!selectedMake ? "isDisabledLink" : ""}`} aria-disabled={!selectedMake}>
            {labels.openBrand}
          </Link>
        </div>
      </div>
    </section>
  );
}
