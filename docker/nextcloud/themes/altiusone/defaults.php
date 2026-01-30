<?php
/**
 * AltiusOne Theme for Nextcloud
 *
 * Custom branding and colors for the AltiusOne ecosystem.
 */

class OC_Theme {

    /**
     * Returns the title
     * @return string Title
     */
    public function getTitle(): string {
        return 'AltiusOne Cloud';
    }

    /**
     * Returns the short name of the software
     * @return string Name
     */
    public function getName(): string {
        return 'AltiusOne Cloud';
    }

    /**
     * Returns the base URL
     * @return string URL
     */
    public function getBaseUrl(): string {
        return 'https://altiusone.ch';
    }

    /**
     * Returns the documentation URL
     * @return string URL
     */
    public function getDocBaseUrl(): string {
        return 'https://docs.altiusone.ch';
    }

    /**
     * Returns the entity (company name)
     * @return string Entity
     */
    public function getEntity(): string {
        return 'AltiusOne';
    }

    /**
     * Returns the slogan
     * @return string Slogan
     */
    public function getSlogan(): string {
        return 'Votre espace cloud sécurisé';
    }

    /**
     * Returns the primary color
     * RGB: 15, 98, 106 = #0F626A (teal)
     * @return string Color
     */
    public function getColorPrimary(): string {
        return '#0F626A';
    }

    /**
     * Returns the background color for the header
     * @return string Color
     */
    public function getColorBackground(): string {
        return '#0F626A';
    }

    /**
     * Returns the text color for the header
     * @return string Color
     */
    public function getColorText(): string {
        return '#FFFFFF';
    }

    /**
     * Returns the mail header color
     * @return string Color
     */
    public function getMailHeaderColor(): string {
        return '#0F626A';
    }

    /**
     * Returns the logo path
     * @return string Path
     */
    public function getLogo(): string {
        return '/themes/altiusone/core/img/logo.png';
    }
}
