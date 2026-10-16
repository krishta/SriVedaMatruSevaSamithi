import { Pipe, PipeTransform } from '@angular/core';

/** Formats amount_paise into Indian-grouped ₹ (e.g. 10000000 -> ₹1,00,000). Never use built-in `currency`. */
@Pipe({ name: 'inrCurrency', standalone: true })
export class InrCurrencyPipe implements PipeTransform {
  transform(amountPaise: number | null | undefined): string {
    if (amountPaise == null) {
      return '—';
    }
    const rupees = Math.floor(amountPaise / 100);
    const s = String(rupees);
    let grouped: string;
    if (s.length <= 3) {
      grouped = s;
    } else {
      const last3 = s.slice(-3);
      let rest = s.slice(0, -3);
      const parts: string[] = [];
      while (rest.length > 2) {
        parts.unshift(rest.slice(-2));
        rest = rest.slice(0, -2);
      }
      if (rest) {
        parts.unshift(rest);
      }
      grouped = parts.join(',') + ',' + last3;
    }
    return `\u20b9${grouped}`;
  }
}