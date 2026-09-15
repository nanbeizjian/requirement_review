import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> { children: ReactNode; }

export function Button({ className, children, ...rest }: Props) {
  return <button className={[styles.btn, className].filter(Boolean).join(" ")} {...rest}>{children}</button>;
}
